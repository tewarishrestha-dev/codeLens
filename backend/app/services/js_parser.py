import re
from pathlib import Path

# Tokenizers and patterns for JavaScript/TypeScript parsing

IMPORT_STATIC_RE = re.compile(
    r"""(?:import|export)\s+(?:[\w*\s{},$]+\s+from\s+)?['"]([^'"]+)['"]""",
    re.MULTILINE
)
REQUIRE_RE = re.compile(
    r"""(?:const|let|var)\s+[\w*\s{},$]+\s*=\s*require\(\s*['"]([^'"]+)['"]\s*\)""",
    re.MULTILINE
)
DYNAMIC_IMPORT_RE = re.compile(
    r"""import\(\s*['"]([^'"]+)['"]\s*\)""",
    re.MULTILINE
)

CLASS_RE = re.compile(
    r"""^[ \t]*(?:export\s+)?(?:default\s+)?class\s+([A-Za-z_$][\w$]*)(?:\s+extends\s+([A-Za-z_$.][\w$.]*))?""",
    re.MULTILINE
)

FUNC_DECL_RE = re.compile(
    r"""^[ \t]*(?:export\s+)?(?:default\s+)?(?:async\s+)?function(?:\s+([A-Za-z_$][\w$]*))?\s*\(([^)]*)\)""",
    re.MULTILINE
)

ARROW_OR_EXPR_RE = re.compile(
    r"""^[ \t]*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:\(([^)]*)\)|([A-Za-z_$][\w$]*))\s*=>""",
    re.MULTILINE
)

METHOD_RE = re.compile(
    r"""^[ \t]+(?:async\s+)?(?:static\s+)?(?:get\s+|set\s+)?([A-Za-z_$][\w$]*)\s*\(([^)]*)\)\s*\{""",
    re.MULTILINE
)

CALL_RE = re.compile(
    r"""\b([A-Za-z_$][\w$]*)\s*\(""",
)

# Common JS/TS keywords and built-ins that are not user function calls
RESERVED_CALLS = {
    "if", "for", "while", "switch", "catch", "return", "throw",
    "typeof", "instanceof", "function", "import", "require",
    "console", "super", "constructor"
}


def _clean_args(args_str: str) -> list[str]:
    """Extract clean parameter names from argument string, ignoring TS types."""
    if not args_str:
        return []
    args = []
    for raw in args_str.split(","):
        arg = raw.strip()
        if not arg:
            continue
        # Strip default values: a = 1 -> a
        arg = arg.split("=")[0].strip()
        # Strip TS type annotations: a: string -> a
        arg = arg.split(":")[0].strip()
        # Strip rest operator: ...args -> args
        arg = arg.lstrip(".")
        if re.match(r"^[A-Za-z_$][\w$]*$", arg):
            args.append(arg)
    return args


def parse_js_file(file_path: Path) -> dict:
    """Parse a JavaScript or TypeScript file and extract symbols.

    Returns dict with identical schema to parse_python_file:
    {
        "imports": list[str],
        "functions": list[dict],
        "classes": list[dict],
        "calls": list[dict]
    }
    """
    try:
        source = file_path.read_text(encoding="utf-8-sig")
    except (UnicodeDecodeError, OSError):
        return {
            "imports": [],
            "functions": [],
            "classes": [],
            "calls": []
        }

    lines = source.splitlines()

    # 1. Imports
    imports_set = set()
    for m in IMPORT_STATIC_RE.finditer(source):
        imports_set.add(m.group(1))
    for m in REQUIRE_RE.finditer(source):
        imports_set.add(m.group(1))
    for m in DYNAMIC_IMPORT_RE.finditer(source):
        imports_set.add(m.group(1))
    imports = sorted(imports_set)

    # 2. Classes and functions line-by-line
    classes = []
    functions = []
    calls = []

    current_class = None
    current_function = None

    for lineno, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
            continue

        # Check for class declaration
        class_match = CLASS_RE.match(line)
        if class_match:
            cls_name = class_match.group(1)
            base_name = class_match.group(2)
            bases = [base_name] if base_name else []
            current_class = {
                "name": cls_name,
                "line": lineno,
                "methods": [],
                "bases": bases
            }
            classes.append(current_class)
            current_function = None
            continue

        # Check for standard function declaration
        func_match = FUNC_DECL_RE.match(line)
        if func_match and func_match.group(1):
            name = func_match.group(1)
            args = _clean_args(func_match.group(2))
            fn_entry = {
                "name": name,
                "line": lineno,
                "arguments": args
            }
            functions.append(fn_entry)
            current_function = name
            continue

        # Check for arrow function or expr: const name = (...) =>
        arrow_match = ARROW_OR_EXPR_RE.match(line)
        if arrow_match:
            name = arrow_match.group(1)
            args_str = arrow_match.group(2) or arrow_match.group(3) or ""
            args = _clean_args(args_str)
            fn_entry = {
                "name": name,
                "line": lineno,
                "arguments": args
            }
            functions.append(fn_entry)
            current_function = name
            continue

        # Check for class method if inside a class
        if current_class:
            method_match = METHOD_RE.match(line)
            if method_match:
                m_name = method_match.group(1)
                m_args = _clean_args(method_match.group(2))
                current_class["methods"].append({
                    "name": m_name,
                    "line": lineno,
                    "arguments": m_args
                })
                current_function = m_name
                continue

        # Track function calls on this line
        for call_m in CALL_RE.finditer(line):
            called = call_m.group(1)
            if called not in RESERVED_CALLS and not called.isdigit():
                calls.append({
                    "function": current_function or "<module>",
                    "calls": called,
                    "line": lineno
                })

    return {
        "imports": imports,
        "functions": functions,
        "classes": classes,
        "calls": calls
    }

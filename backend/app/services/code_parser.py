import ast
from pathlib import Path


def _base_name(node):
    """Best-effort simple name of a base-class expression.

    Handles ``Name`` (``Base``), ``Attribute`` (``module.Base`` -> ``Base``) and
    ``Subscript`` (``Generic[T]`` -> ``Generic``). Anything else is ignored, so
    dynamic or otherwise unsupported bases degrade gracefully.
    """
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        return node.attr

    if isinstance(node, ast.Subscript):
        return _base_name(node.value)

    return None


def _base_names(bases):
    names = []

    for base in bases:
        name = _base_name(base)

        if name and name not in names:
            names.append(name)

    return names


def parse_python_file(file_path: Path):
    try:
        source = file_path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return {
            "imports": [],
            "functions": [],
            "classes": []
        }

    tree = ast.parse(source)

    imports = []
    functions = []
    classes = []
    calls = []

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    if isinstance(child.func, ast.Name):
                        calls.append({
                            "function": node.name,
                            "calls": child.func.id,
                            "line": child.lineno
                        })

                    elif isinstance(child.func, ast.Attribute):
                        calls.append({
                            "function": node.name,
                            "calls": child.func.attr,
                            "line": child.lineno
                        })
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append({
                "name": node.name,
                "line": node.lineno,
                "arguments": [arg.arg for arg in node.args.args]
            })

        elif isinstance(node, ast.ClassDef):
            methods = []

            for method in node.body:
                if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    methods.append({
                        "name": method.name,
                        "line": method.lineno,
                        "arguments": [arg.arg for arg in method.args.args]
                    })

            classes.append({
                "name": node.name,
                "line": node.lineno,
                "methods": methods,
                "bases": _base_names(node.bases)
            })

    return {
        "imports": imports,
        "functions": functions,
        "classes": classes,
        "calls": calls,
    }
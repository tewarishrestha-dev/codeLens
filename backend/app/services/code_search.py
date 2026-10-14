import re
from pathlib import Path

from .file_reader import read_file


STOP_WORDS = {
    "what", "does", "do", "the", "is",
    "a", "an", "how", "why", "where",
    "this", "that", "function", "class",
    "in", "it", "its", "and", "or", "of",
    "to", "for", "on", "with", "from", "as",
    "by", "at", "into", "over", "than", "then",
    "when", "which", "who", "whom", "also",
    "such", "about", "explain", "explanation",
    "cite", "exact", "line", "lines", "purpose",
    "distinguish", "between", "mechanism",
    "py", "s", "click",
}

BODY_WEIGHT = 5
NAME_WEIGHT = 3
IMPORT_WEIGHT = 1

# A match whose identifier is named in the query is the most relevant
# evidence we can surface, so it always outranks body-text matches.
NAME_RELEVANCE = 1000

# Lines at the top of a definition (signature + leading docstring) are
# stronger evidence than a keyword buried deep inside the body.
HEADER_LINES = 5

_WORD_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_PATH_RE = re.compile(r"[A-Za-z0-9_./\\-]+")

# Test/fixture files are keyword-rich (they mention ``command``, ``invoke``,
# ``execution`` constantly) and would otherwise crowd the real implementation
# out of the limited context window, starving the model of the evidence it
# needs. They are still returned, but ranked below non-test matches.
_TEST_PATH_RE = re.compile(
    r"(^|/)(tests?|testing|specs?|__tests__|fixtures?|mocks?|stubs?)/"
    r"|(^|/)(test_[^/]*|[^/]*_test|[^/]*_spec)\.py$"
    r"|\.test\.[^/]+$"
    r"|\.spec\.[^/]+$"
    r"|(^|/)conftest\.py$"
)


def _is_test_file(file_path):
    normalized = file_path.replace("\\", "/").lower()
    return _TEST_PATH_RE.search(normalized) is not None


def _keywords(query):
    tokens = _WORD_RE.findall(query.lower())
    keywords = []

    for token in tokens:
        if token in STOP_WORDS:
            continue

        if token not in keywords:
            keywords.append(token)

    return keywords


def _contains_word(text, keyword):
    return re.search(
        r"\b" + re.escape(keyword) + r"\b",
        text
    ) is not None


def _named_paths(query):
    """Path-like tokens from a query (e.g. ``examples/foo/foo.py``)."""
    paths = []

    for token in _PATH_RE.findall(query.lower()):
        if "/" in token or "\\" in token or token.endswith(".py"):
            paths.append(token)

    return paths


def _is_named_file(named_paths, file_path):
    """True only when the query clearly identifies this repository path."""
    normalized = file_path.replace("\\", "/").lower()
    base = normalized.split("/")[-1]

    for token in named_paths:
        candidate = token.replace("\\", "/").lstrip("./")

        if not candidate:
            continue

        if (
            candidate == normalized
            or candidate == base
            or normalized.endswith("/" + candidate)
        ):
            return True

    return False


def _definitions(data):
    definitions = []

    for function in data.get("functions", []):
        definitions.append({
            "type": "function",
            "name": function["name"],
            "line": function["line"],
            "class": None
        })

    for cls in data.get("classes", []):
        definitions.append({
            "type": "class",
            "name": cls["name"],
            "line": cls["line"],
            "class": None
        })

        for method in cls.get("methods", []):
            definitions.append({
                "type": "method",
                "name": method["name"],
                "line": method["line"],
                "class": cls["name"]
            })

    definitions.sort(key=lambda item: item["line"])

    return definitions


def _canonical_lines(definitions):
    """Map (class, name) to the last definition line.

    Later definitions override earlier ones in Python, so the last one is the
    effective implementation (this skips ``@overload`` stubs that precede the
    real definition).
    """
    lines = {}

    for definition in definitions:
        key = (definition["class"], definition["name"])
        lines[key] = max(lines.get(key, 0), definition["line"])

    return lines


def _owner_for_line(definitions, line):
    owner = None

    for definition in definitions:
        if definition["line"] <= line:
            owner = definition
        else:
            break

    return owner


def _name_matches(data, keywords):
    matches = []

    for keyword in keywords:
        for function in data.get("functions", []):
            if _contains_word(function["name"].lower(), keyword):
                matches.append({
                    "type": "function",
                    "name": function["name"],
                    "line": function["line"],
                    "class": None,
                    "reason": "name",
                    "relevance": NAME_RELEVANCE
                })

        for cls in data.get("classes", []):
            if _contains_word(cls["name"].lower(), keyword):
                matches.append({
                    "type": "class",
                    "name": cls["name"],
                    "line": cls["line"],
                    "class": None,
                    "reason": "name",
                    "relevance": NAME_RELEVANCE
                })

            for method in cls.get("methods", []):
                if _contains_word(method["name"].lower(), keyword):
                    matches.append({
                        "type": "method",
                        "name": method["name"],
                        "line": method["line"],
                        "class": cls["name"],
                        "reason": "name",
                        "relevance": NAME_RELEVANCE
                    })

        for imported in data.get("imports", []):
            if _contains_word(imported.lower(), keyword):
                matches.append({
                    "type": "import",
                    "name": imported,
                    "class": None,
                    "reason": "name",
                    "relevance": IMPORT_WEIGHT
                })

    return matches


def _named_classes(code_analysis, keywords, named_paths=None):
    """Class identities the query clearly identifies (same rule as name matches).

    Identities are ``(file path, class name)`` pairs so same-named classes in
    different modules stay distinct. When the query names specific files, only
    classes in those files are considered, so a path-qualified query cannot
    activate hierarchy expansion in an unrelated module. Only these classes
    (and their subclasses) activate inheritance expansion, so a generic query
    that names no class never expands the hierarchy.
    """
    named = set()

    for file_path, data in code_analysis.items():
        if named_paths and not _is_named_file(named_paths, file_path):
            continue

        for cls in data.get("classes", []):
            name = cls.get("name", "")

            if any(_contains_word(name.lower(), keyword) for keyword in keywords):
                named.add((file_path, name))

    return named


def _class_bases(code_analysis):
    """Map each class identity to its resolved direct base identities.

    Identities are ``(file path, class name)`` pairs. Bases come from the
    parser's ``bases`` field (simple names; qualified bases such as
    ``cli.Command`` are recorded as ``Command``). A base name is resolved
    within the same module when that module defines it, otherwise to a unique
    same-named class elsewhere in the repository; ambiguous or unknown bases
    are dropped so unrelated same-named classes never link.
    """
    local_names = {}
    owners = {}

    for file_path, data in code_analysis.items():
        defined = set()

        for cls in data.get("classes", []):
            name = cls.get("name")

            if not name:
                continue

            defined.add(name)
            owners.setdefault(name, set()).add(file_path)

        local_names[file_path] = defined

    bases = {}

    for file_path, data in code_analysis.items():
        for cls in data.get("classes", []):
            name = cls.get("name")

            if not name:
                continue

            direct = bases.setdefault((file_path, name), [])

            for base in cls.get("bases", []):
                if not base:
                    continue

                base_name = base.split(".")[-1]

                if not base_name or base_name == name:
                    continue

                if base_name in local_names[file_path]:
                    resolved = (file_path, base_name)
                else:
                    candidates = owners.get(base_name, set())

                    if len(candidates) != 1:
                        continue

                    resolved = (next(iter(candidates)), base_name)

                if resolved not in direct:
                    direct.append(resolved)

    return bases


def _related_classes(named_classes, class_bases):
    """Named class identities plus all transitive subclasses (cycle-safe)."""
    if not named_classes:
        return set()

    children = {}

    for name, direct_bases in class_bases.items():
        for base in direct_bases:
            children.setdefault(base, set()).add(name)

    related = set()
    queue = list(named_classes)

    while queue:
        current = queue.pop()

        if current in related:
            continue

        related.add(current)

        for child in children.get(current, ()):
            if child not in related:
                queue.append(child)

    return related


def _inherited_matches(file_path, data, related, canonical, existing):
    """Methods of a named class identity or its subclasses not already surfaced.

    These are added so a subclass method such as ``Group.invoke`` appears even
    when its body has no query-keyword evidence. Existing matches are never
    duplicated.
    """
    present = {(match.get("class"), match["name"]) for match in existing}
    matches = []

    for cls in data.get("classes", []):
        class_name = cls.get("name")

        if (file_path, class_name) not in related:
            continue

        for method in cls.get("methods", []):
            key = (class_name, method["name"])

            if key in present:
                continue

            present.add(key)

            matches.append({
                "type": "method",
                "name": method["name"],
                "line": canonical.get(key, method.get("line")),
                "class": class_name,
                "reason": "inherited",
                "relevance": NAME_RELEVANCE - 1
            })

    return matches


def _body_matches(repo_path, file_path, data, keywords, canonical):
    if repo_path is None:
        return []

    try:
        source = read_file(Path(repo_path), file_path)
    except Exception:
        return []

    definitions = _definitions(data)
    found = {}
    header = {}

    for number, text in enumerate(source.splitlines(), start=1):
        lowered = text.lower()
        owner = _owner_for_line(definitions, number)

        if owner is None or owner["type"] == "class":
            continue

        key = (owner["class"], owner["name"])

        for keyword in keywords:
            if not _contains_word(lowered, keyword):
                continue

            found.setdefault(key, set()).add(keyword)

            if number <= owner["line"] + HEADER_LINES:
                header.setdefault(key, set()).add(keyword)

    matches = []

    for key, keywords_found in found.items():
        class_name, name = key
        line = canonical.get(key, None)

        if line is None:
            continue

        relevance = len(keywords_found) + len(header.get(key, set()))

        matches.append({
            "type": "method" if class_name else "function",
            "name": name,
            "line": line,
            "class": class_name,
            "reason": "body",
            "relevance": relevance
        })

    return matches


def _weight(match):
    if match.get("reason") == "body":
        return BODY_WEIGHT

    if match["type"] == "import":
        return IMPORT_WEIGHT

    return NAME_WEIGHT


def _canonicalize(matches, canonical):
    for match in matches:
        key = (match.get("class"), match["name"])
        match["line"] = canonical.get(key, match.get("line"))
    return matches


def _dedupe(matches):
    unique = []
    seen = set()

    for match in matches:
        key = (
            match.get("class"),
            match["name"],
            match.get("line"),
            match.get("reason")
        )

        if key in seen:
            continue

        seen.add(key)
        unique.append(match)

    return unique


def _match_sort_key(match):
    line = match.get("line")

    return (
        -match.get("relevance", 0),
        -_weight(match),
        line if line is not None else float("inf"),
        match["name"]
    )


def search_code(code_analysis, query, repo_path=None):
    keywords = _keywords(query)

    if not keywords:
        return []

    named_paths = _named_paths(query)

    # Inheritance expansion is only active when the query clearly names a
    # class; methods of that class and its transitive subclasses then become
    # first-class evidence (e.g. Group.invoke for a "Command" query).
    related = _related_classes(
        _named_classes(code_analysis, keywords, named_paths),
        _class_bases(code_analysis)
    )

    results = []

    for file_path, data in code_analysis.items():
        canonical = _canonical_lines(_definitions(data))

        matches = _name_matches(data, keywords)
        matches += _body_matches(
            repo_path, file_path, data, keywords, canonical
        )

        if related:
            matches += _inherited_matches(
                file_path, data, related, canonical, matches
            )

        matches = _canonicalize(matches, canonical)
        matches = _dedupe(matches)

        if not matches:
            continue

        # Methods belonging to a named class or one of its subclasses outrank
        # unrelated body-text matches (but not the explicitly named class).
        if related:
            for match in matches:
                if (file_path, match.get("class")) in related:
                    match["relevance"] = max(
                        match.get("relevance", 0),
                        NAME_RELEVANCE - 1
                    )

        matches.sort(key=_match_sort_key)

        # Inherited matches guarantee inclusion but must not inflate the
        # file-level ranking score.
        score = sum(
            _weight(match)
            for match in matches
            if match.get("reason") != "inherited"
        )

        results.append({
            "file": file_path,
            "matches": matches,
            "score": score,
            "named": _is_named_file(named_paths, file_path),
            "test": _is_test_file(file_path),
        })

    # Explicitly-named paths always win. Otherwise rank by score, but keep
    # test files below real source so keyword-rich tests cannot crowd the
    # implementation out of the context window.
    results.sort(
        key=lambda item: (
            not item["named"],
            item["test"],
            -item["score"],
            item["file"],
        )
    )

    return results

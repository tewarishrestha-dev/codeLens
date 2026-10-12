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
    results = []

    for file_path, data in code_analysis.items():
        canonical = _canonical_lines(_definitions(data))

        matches = _canonicalize(
            _name_matches(data, keywords)
            + _body_matches(repo_path, file_path, data, keywords, canonical),
            canonical
        )

        matches = _dedupe(matches)

        if not matches:
            continue

        # A class named in the query makes its own methods first-class
        # evidence, so promote them above unrelated body-text matches.
        named_classes = {
            match["name"]
            for match in matches
            if match.get("type") == "class" and match.get("reason") == "name"
        }

        if named_classes:
            for match in matches:
                if match.get("class") in named_classes:
                    match["relevance"] = max(
                        match.get("relevance", 0),
                        NAME_RELEVANCE - 1
                    )

        matches.sort(key=_match_sort_key)

        score = sum(_weight(match) for match in matches)

        results.append({
            "file": file_path,
            "matches": matches,
            "score": score,
            "named": _is_named_file(named_paths, file_path)
        })

    results.sort(
        key=lambda item: (not item["named"], -item["score"], item["file"])
    )

    return results

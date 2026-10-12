from pathlib import Path

from .file_reader import read_file
from .call_analyzer import resolve_call_targets


MAX_CONTEXT_FILES = 5
MAX_ENTRIES_PER_FILE = 40
MAX_SOURCE_LINES = 60
MAX_EXPANSION_MATCHES = 3


def _cap_source(source):
    lines = source.splitlines()

    if len(lines) <= MAX_SOURCE_LINES:
        return source

    omitted = len(lines) - MAX_SOURCE_LINES

    return "\n".join(lines[:MAX_SOURCE_LINES]) + (
        f"\n... ({omitted} more lines omitted)"
    )


def _indentation(line):
    return len(line) - len(line.lstrip(" \t"))


def get_function_source(source, function):
    lines = source.splitlines()

    start = function["line"] - 1

    if start < 0 or start >= len(lines):
        return ""

    def_indent = _indentation(lines[start])
    end = len(lines)

    for i in range(start + 1, len(lines)):
        if not lines[i].strip():
            continue

        if _indentation(lines[i]) <= def_indent:
            end = i
            break

    return "\n".join(lines[start:end])


def find_function_definition(data, function_name, class_name=None, line=None):
    """Locate a top-level function or class method by name within a file.

    When ``class_name`` is given, only methods of that class are considered.
    When ``line`` is given, the definition declared exactly at that line wins
    (this disambiguates ``@overload`` stubs from the real implementation).
    Otherwise the last matching definition is returned, matching Python's
    "later definition overrides earlier" semantics.
    """
    candidates = []

    if class_name is None:
        for item in data.get("functions", []):
            if item["name"] == function_name:
                candidates.append(item)

        for cls in data.get("classes", []):
            for method in cls.get("methods", []):
                if method["name"] == function_name:
                    candidates.append(method)
    else:
        for cls in data.get("classes", []):
            if cls["name"] != class_name:
                continue

            for method in cls.get("methods", []):
                if method["name"] == function_name:
                    candidates.append(method)

    if not candidates:
        return None

    if line is not None:
        for candidate in candidates:
            if candidate["line"] == line:
                return candidate

    return candidates[-1]


def number_lines(source, start_line):
    return "\n".join(
        f"{start_line + i}: {line}"
        for i, line in enumerate(source.splitlines())
    )



def get_function_entry(
    repo_path,
    code_analysis,
    file_path,
    function_name,
    class_name=None,
    line=None
):
    data = code_analysis.get(file_path)

    if not data:
        return None

    function = find_function_definition(data, function_name, class_name, line)

    if not function:
        return None

    source = read_file(
        Path(repo_path),
        file_path
    )

    return {
        "name": function["name"],
        "type": "function",
        "file": file_path,
        "line": function["line"],
        "source": number_lines(
            _cap_source(get_function_source(source, function)),
            function["line"]
        )
    }


def get_function(
    repo_path,
    code_analysis,
    call_graph,
    file_path,
    function_name,
    visited,
    class_name=None,
    line=None
):
    key = (file_path, class_name, function_name)

    if key in visited:
        return []

    visited.add(key)

    entry = get_function_entry(
        repo_path,
        code_analysis,
        file_path,
        function_name,
        class_name,
        line
    )

    if entry is None:
        return []

    results = [entry]

    calls = call_graph.get(file_path, {}).get(
        function_name,
        []
    )

    for call in calls:
        for target_file, _target_line in resolve_call_targets(call):
            if not isinstance(target_file, str):
                continue

            results.extend(
                get_function(
                    repo_path,
                    code_analysis,
                    call_graph,
                    target_file,
                    call["calls"],
                    visited
                )
            )

    return results


def build_context(
    repo_path,
    code_analysis,
    search_results,
    call_graph
):
    context = []

    for result in search_results[:MAX_CONTEXT_FILES]:
        file_path = result["file"]
        data = code_analysis.get(file_path)

        if not data:
            continue

        # Rank by relevance (explicitly named definitions and functions with
        # stronger source-body evidence first), never by line number alone.
        matches = _prioritized_matches(result["matches"])

        relevant_code = []

        # Always surface the matched definitions themselves first, so the
        # ranked matches are never crowded out by call-chain expansion.
        for match in matches:
            if match["type"] in ("function", "method"):
                entry = get_function_entry(
                    repo_path,
                    code_analysis,
                    file_path,
                    match["name"],
                    class_name=match.get("class"),
                    line=match.get("line")
                )

                if entry:
                    relevant_code.append(entry)
            elif match["type"] == "class":
                relevant_code.append(
                    _class_entry(repo_path, file_path, match)
                )

        # Then add call-chain context for the highest-ranked matches only.
        visited = set()

        for match in matches[:MAX_EXPANSION_MATCHES]:
            if match["type"] not in ("function", "method"):
                continue

            relevant_code.extend(
                get_function(
                    repo_path,
                    code_analysis,
                    call_graph,
                    file_path,
                    match["name"],
                    visited,
                    class_name=match.get("class"),
                    line=match.get("line")
                )
            )

        context.append({
            "file": file_path,
            "code": _unique_code(relevant_code)[:MAX_ENTRIES_PER_FILE],
            "matches": matches,
            "imports": data.get("imports", [])
        })

    return context


def _prioritized_matches(matches):
    def sort_key(match):
        line = match.get("line")

        return (
            -match.get("relevance", 0),
            line if line is not None else float("inf"),
            match["name"]
        )

    return sorted(matches, key=sort_key)


def _class_entry(repo_path, file_path, match):
    source = read_file(Path(repo_path), file_path)
    lines = source.splitlines()
    start = match["line"] - 1
    end = len(lines)

    for i in range(start + 1, len(lines)):
        if lines[i] and not lines[i].startswith((" ", "\t")):
            end = i
            break

    return {
        "name": match["name"],
        "type": "class",
        "file": file_path,
        "line": match["line"],
        "source": number_lines(
            _cap_source("\n".join(lines[start:end])),
            start + 1
        )
    }


def _unique_code(entries):
    unique = []
    seen = set()

    for entry in entries:
        key = (entry["file"], entry["name"], entry["line"])

        if key in seen:
            continue

        seen.add(key)
        unique.append(entry)

    return unique

def build_project_context(repository):
    architecture = repository["architecture"]

    files = {}

    for file_path in architecture["files"]:
        try:
            files[file_path] = read_file(
                Path(repository["path"]),
                file_path
            )
        except Exception:
            files[file_path] = ""

    return {
        "project_name": repository["name"],
        "files": architecture["files"],
        "file_count": architecture["file_count"],
        "functions": architecture["functions"],
        "classes": architecture["classes"],
        "entry_points": architecture["entry_points"],
        "dependencies": architecture["dependencies"],
        "directories": architecture["directories"],
        "imports": {
            file_path: data.get("imports", [])
            for file_path, data in repository["code_analysis"].items()
        },
        "source_code": files,
    }
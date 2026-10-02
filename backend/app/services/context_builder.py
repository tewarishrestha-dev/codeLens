from pathlib import Path

from .file_reader import read_file


def get_function_source(source, function):
    lines = source.splitlines()

    start = function["line"] - 1
    end = len(lines)

    for i in range(start + 1, len(lines)):
        if lines[i] and not lines[i].startswith((" ", "\t")):
            end = i
            break

    return "\n".join(lines[start:end])


def get_function(
    repo_path,
    code_analysis,
    call_graph,
    file_path,
    function_name,
    visited
):
    key = (file_path, function_name)

    if key in visited:
        return []

    visited.add(key)

    data = code_analysis.get(file_path)

    if not data:
        return []

    function = next(
        (
            item
            for item in data["functions"]
            if item["name"] == function_name
        ),
        None
    )

    if not function:
        return []

    source = read_file(
        Path(repo_path),
        file_path
    )

    results = [{
        "name": function["name"],
        "type": "function",
        "file": file_path,
        "line": function["line"],
        "source": get_function_source(
            source,
            function
        )
    }]

    calls = call_graph.get(file_path, {}).get(
        function_name,
        []
    )

    for call in calls:
        target_file = call["target_file"]

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

    for result in search_results:
        file_path = result["file"]
        data = code_analysis.get(file_path)

        if not data:
            continue

        relevant_code = []
        visited = set()

        for match in result["matches"]:
            if match["type"] != "function":
                continue

            relevant_code.extend(
                get_function(
                    repo_path,
                    code_analysis,
                    call_graph,
                    file_path,
                    match["name"],
                    visited
                )
            )

        context.append({
            "file": file_path,
            "code": relevant_code,
            "matches": result["matches"],
            "imports": data.get("imports", [])
        })

    return context

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
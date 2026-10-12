from pathlib import Path


def build_call_graph(code_analysis):
    functions = {}

    for file_path, data in code_analysis.items():
        for function in data["functions"]:
            functions.setdefault(function["name"], []).append({
                "file": file_path,
                "line": function["line"]
            })

        for cls in data["classes"]:
            for method in cls["methods"]:
                functions.setdefault(method["name"], []).append({
                    "file": file_path,
                    "line": method["line"]
                })

    graph = {}

    for file_path, data in code_analysis.items():
        graph[file_path] = {}

        for function in data["functions"]:
            graph[file_path][function["name"]] = []

        for cls in data["classes"]:
            for method in cls["methods"]:
                graph[file_path][method["name"]] = []

        for call in data["calls"]:
            targets = functions.get(call["calls"], [])

            if not targets:
                continue

            call_data = {
                "calls": call["calls"],
                "line": call["line"],
                "target_file": (
                    targets[0]["file"]
                    if len(targets) == 1
                    else [target["file"] for target in targets]
                ),
                "target_line": (
                    targets[0]["line"]
                    if len(targets) == 1
                    else [target["line"] for target in targets]
                ),
                "targets": [
                    {"file": target["file"], "line": target["line"]}
                    for target in targets
                ],
                "ambiguous": len(targets) > 1,
            }

            graph[file_path].setdefault(
                call["function"],
                []
            ).append(call_data)

    return graph


def resolve_call_targets(call):
    """Return every candidate (file_path, line) target for a call edge.

    Ambiguous calls (a name defined in more than one place) return all
    candidates instead of being filtered out by the consumer. Falls back to
    the legacy ``target_file``/``target_line`` shape when ``targets`` is
    absent.
    """
    targets = call.get("targets")

    if targets:
        return [
            (target["file"], target.get("line"))
            for target in targets
        ]

    target_file = call.get("target_file")
    target_line = call.get("target_line")

    if isinstance(target_file, str):
        return [(target_file, target_line)]

    if isinstance(target_file, list):
        lines = (
            target_line
            if isinstance(target_line, list)
            else [None] * len(target_file)
        )
        return list(zip(target_file, lines))

    return []


def build_execution_flow(call_graph, entry_point):
    flow = []
    visited = set()

    def walk(file_path, function_name=None, line=None):
        key = (file_path, function_name)

        if key in visited:
            return

        visited.add(key)

        flow.append({
            "file": file_path,
            "function": function_name,
            "line": line
        })

        functions = call_graph.get(file_path, {})

        if function_name is None:
            return

        for call in functions.get(function_name, []):
            for target_file, target_line in resolve_call_targets(call):
                if not isinstance(target_file, str):
                    continue

                walk(
                    target_file,
                    call["calls"],
                    target_line
                )

    # Find functions that are never called by another function.
    called_functions = set()

    for file_functions in call_graph.values():
        for calls in file_functions.values():
            for call in calls:
                called_functions.add(call["calls"])

    entry_file_functions = call_graph.get(entry_point, {})

    root_functions = [
        name
        for name in entry_file_functions
        if name not in called_functions
    ]

    for function_name in root_functions:
        walk(entry_point, function_name)

    return flow
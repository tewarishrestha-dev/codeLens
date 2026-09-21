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
                )
            }

            graph[file_path].setdefault(
                call["function"],
                []
            ).append(call_data)

    return graph


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

        if not function_name:
            for function in functions:
                walk(file_path, function)

            return

        calls = functions.get(function_name, [])
        
        for call in calls:
            target_file = call["target_file"]

            if not isinstance(target_file, str):
                continue

            walk(
                target_file,
                call["calls"],
                call.get("target_line")
            )

    walk(entry_point)

    return flow
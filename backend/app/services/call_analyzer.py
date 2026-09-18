from pathlib import Path


def build_call_graph(code_analysis):
    functions = {}

    for file_path, data in code_analysis.items():
        for function in data["functions"]:
            functions.setdefault(function["name"], []).append(file_path)

        for cls in data["classes"]:
            for method in cls["methods"]:
                functions.setdefault(method["name"], []).append(file_path)

    graph = {}

    for file_path, data in code_analysis.items():
        graph[file_path] = []

        for call in data["calls"]:
            targets = functions.get(call["calls"], [])
            target = targets[0] if len(targets) == 1 else targets

            graph[file_path].append({
                "function": call["function"],
                "calls": call["calls"],
                "target_file": target
            })

    return graph
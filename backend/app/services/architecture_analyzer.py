from pathlib import Path
def build_architecture_summary(
    code_analysis,
    dependencies,
    entry_points,
):
    files = list(code_analysis.keys())

    functions = []
    classes = []

    for file_path, data in code_analysis.items():
        for function in data["functions"]:
            functions.append({
                "name": function["name"],
                "file": file_path,
                "line": function["line"],
            })

        for cls in data["classes"]:
            classes.append({
                "name": cls["name"],
                "file": file_path,
                "line": cls["line"],
            })

    dependency_edges = []

    for source, targets in dependencies["forward"].items():
        for target in targets:
            dependency_edges.append({
                "from": source,
                "to": target,
            })

            
    directories = {}

    for file in files:
        parts = Path(file).parts

        if len(parts) > 1:
            directory = str(Path(*parts[:-1]))
        else:
            directory = "root"

        directories.setdefault(directory, []).append(file)

    return {
    "files": files,
    "file_count": len(files),
    "functions": functions,
    "function_count": len(functions),
    "classes": classes,
    "class_count": len(classes),
    "entry_points": entry_points,
    "dependencies": dependency_edges,
    "dependency_count": len(dependency_edges),
    "directories": directories,
    "directory_count": len(directories),
}
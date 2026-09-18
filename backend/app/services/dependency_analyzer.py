from pathlib import Path


def build_dependencies(code_analysis):
    dependencies = {}
    files = {}

    for path in code_analysis:
        module = Path(path).with_suffix("").as_posix().replace(".", "/")
        module = module.replace("\\", "/")
        files[module] = path

    for file_path, data in code_analysis.items():
        dependencies[file_path] = []

    reverse_dependencies = {path: [] for path in code_analysis}

    for file_path, data in code_analysis.items():
        for module in data["imports"]:
            module = module.replace(".", "/")

            if module.startswith("backend/"):
                module = module[len("backend/"):]

            target = files.get(module)

            if target:
                if target not in dependencies[file_path]:
                    dependencies[file_path].append(target)
                if file_path not in reverse_dependencies[target]:
                    reverse_dependencies[target].append(file_path)

    return {
        "forward": dependencies,
        "reverse": reverse_dependencies
    }
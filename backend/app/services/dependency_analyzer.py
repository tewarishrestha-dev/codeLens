from pathlib import Path


def _resolve_relative_import(base_dir: str, rel_path: str, files_map: dict, all_paths: set) -> str | None:
    """Resolve a relative JavaScript/TypeScript import (e.g. ./api or ../components/FileTree)."""
    parts = []
    base_parts = [p for p in base_dir.replace("\\", "/").split("/") if p and p != "."]
    for seg in rel_path.replace("\\", "/").split("/"):
        if seg == "." or not seg:
            continue
        if seg == "..":
            if base_parts:
                base_parts.pop()
        else:
            base_parts.append(seg)
    candidate_stem = "/".join(base_parts)

    # 1. Exact match in files_map (stem lookup)
    if candidate_stem in files_map:
        return files_map[candidate_stem]

    # 2. Match with extensions (.js, .jsx, .ts, .tsx, .py)
    for ext in [".js", ".jsx", ".ts", ".tsx", ".py"]:
        full = candidate_stem + ext
        if full in all_paths:
            return full

    # 3. Index file match: ./components -> ./components/index.js
    for ext in [".js", ".jsx", ".ts", ".tsx"]:
        index_file = f"{candidate_stem}/index{ext}"
        if index_file in all_paths:
            return index_file

    return None


def build_dependencies(code_analysis):
    dependencies = {}
    files = {}
    all_paths = set(code_analysis.keys())

    for path in code_analysis:
        module = Path(path).with_suffix("").as_posix().replace(".", "/")
        module = module.replace("\\", "/")
        files[module] = path

    for file_path in code_analysis:
        dependencies[file_path] = []

    reverse_dependencies = {path: [] for path in code_analysis}

    for file_path, data in code_analysis.items():
        file_dir = str(Path(file_path).parent.as_posix())
        if file_dir == ".":
            file_dir = ""

        for raw_import in data["imports"]:
            target = None

            # Check if it's a relative path (common in JS/TS)
            if raw_import.startswith("."):
                target = _resolve_relative_import(file_dir, raw_import, files, all_paths)

            if not target:
                module = raw_import.replace(".", "/")

                if module.startswith("backend/"):
                    module = module[len("backend/"):]

                target = files.get(module)

            if target and target != file_path:
                if target not in dependencies[file_path]:
                    dependencies[file_path].append(target)
                if file_path not in reverse_dependencies[target]:
                    reverse_dependencies[target].append(file_path)

    return {
        "forward": dependencies,
        "reverse": reverse_dependencies
    }

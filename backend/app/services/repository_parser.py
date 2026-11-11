from pathlib import Path
from .code_parser import parse_python_file
from .js_parser import parse_js_file

IGNORED_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}
JS_EXTENSIONS = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}


def parse_repository(repo_path: Path):
    results = {}

    for file_path in repo_path.rglob("*"):
        if not file_path.is_file():
            continue

        if any(part in IGNORED_DIRS for part in file_path.parts):
            continue

        suffix = file_path.suffix.lower()
        relative_path = file_path.relative_to(repo_path).as_posix()

        if suffix == ".py":
            results[relative_path] = parse_python_file(file_path)
        elif suffix in JS_EXTENSIONS:
            results[relative_path] = parse_js_file(file_path)

    return results

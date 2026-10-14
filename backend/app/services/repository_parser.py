from pathlib import Path
from .code_parser import parse_python_file


def parse_repository(repo_path: Path):
    results = {}

    for file_path in repo_path.rglob("*.py"):
        if any(part in {".git", "__pycache__", ".venv", "venv"} for part in file_path.parts):
            continue

        # as_posix() normalizes to forward slashes so keys are consistent
        # across platforms (Windows would otherwise yield backslashes and
        # break frontend lookups and flow entry-point round-trips).
        relative_path = file_path.relative_to(repo_path).as_posix()
        results[relative_path] = parse_python_file(file_path)

    return results
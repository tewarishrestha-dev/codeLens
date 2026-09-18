from pathlib import Path


def read_file(repo_path: Path, relative_path: str):
    repo_path = repo_path.resolve()
    file_path = (repo_path / relative_path).resolve()

    if not file_path.is_relative_to(repo_path):
        raise ValueError("File is outside repository")

    return file_path.read_text(
        encoding="utf-8",
        errors="replace"
    )
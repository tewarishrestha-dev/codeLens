from pathlib import Path
from .file_reader import read_file
SOURCE_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx",
    ".java", ".cpp", ".c", ".h",
    ".html", ".css", ".json", ".yaml", ".yml",
    ".md", ".txt"
}


def scan_repository(repo_path: Path):
    def build_tree(path: Path):

        node = {
            "name": path.name,
            "type": "directory" if path.is_dir() else "file",
            "source": path.suffix.lower() in SOURCE_EXTENSIONS
        }


        if path.is_dir():

            node["children"] = [
                build_tree(child)
                for child in sorted(path.iterdir())
                if not any(
                    part in {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}
                    for part in child.parts
                )
            ]

        return node

    return build_tree(repo_path)
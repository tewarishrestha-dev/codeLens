from pathlib import Path
from app.services.file_reader import read_file

repo_path = Path("E:/CodeLens/test_project")

content = read_file(repo_path, "main.py")

print(content)
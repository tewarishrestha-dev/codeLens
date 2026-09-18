from pathlib import Path
from app.services.code_parser import parse_python_file

file_path = Path("E:/CodeLens/test_project/main.py")

result = parse_python_file(file_path)

print(result)
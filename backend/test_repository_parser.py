from pathlib import Path
from app.services.repository_parser import parse_repository

repo_path = Path("E:/CodeLens/backend")

result = parse_repository(repo_path)

for file, data in result.items():
    print("\nFILE:", file)
    print(data)
from app.services.github_service import clone_repository
from app.services.repository_scanner import scan_repository

repo = clone_repository(
    "https://github.com/tewarishrestha-dev/deep_learning"
)

result = scan_repository(repo)

print("Directories:")
for directory in result["directories"]:
    print(directory)

print("\nFiles:")
for file in result["files"]:
    print(file)
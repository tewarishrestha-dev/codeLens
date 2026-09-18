from pathlib import Path
from app.services.zip_service import extract_zip

zip_file = Path("test.zip")

result = extract_zip(zip_file)

print("Extracted to:", result)
print("Files:")

for file in result.rglob("*"):
    print(file.relative_to(result))
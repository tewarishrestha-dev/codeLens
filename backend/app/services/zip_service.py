from pathlib import Path
import tempfile
import zipfile


def extract_zip(file_path: Path) -> Path:
    temp_dir = Path(tempfile.mkdtemp(dir="E:/CodeLensData"))

    with zipfile.ZipFile(file_path, "r") as zip_ref:
        zip_ref.extractall(temp_dir)

    return temp_dir

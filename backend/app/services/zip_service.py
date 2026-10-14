from pathlib import Path
import tempfile
import zipfile

from .repository_store import data_dir


def extract_zip(file_path: Path) -> Path:
    storage_dir = data_dir()
    storage_dir.mkdir(parents=True, exist_ok=True)
    temp_dir = Path(tempfile.mkdtemp(dir=str(storage_dir)))

    with zipfile.ZipFile(file_path, "r") as zip_ref:
        zip_ref.extractall(temp_dir)

    return temp_dir

import requests
from pathlib import Path
import tempfile
import zipfile

from .repository_store import data_dir


def clone_repository(url: str):
    repo_name = url.rstrip("/").split("/")[-1].replace(".git", "")
    base_url = url.rstrip("/")
    zip_url = f"{base_url}/archive/refs/heads/main.zip"

    response = requests.get(zip_url)

    if response.status_code == 404:
        zip_url = f"{base_url}/archive/refs/heads/master.zip"
        response = requests.get(zip_url)

    response.raise_for_status()

    storage_dir = data_dir()
    storage_dir.mkdir(parents=True, exist_ok=True)
    temp_dir = Path(tempfile.mkdtemp(dir=str(storage_dir)))
    zip_path = temp_dir / "repo.zip"

    zip_path.write_bytes(response.content)

    with zipfile.ZipFile(zip_path) as z:
        z.extractall(temp_dir)

    extracted = next(p for p in temp_dir.iterdir() if p.is_dir())

    return extracted, repo_name
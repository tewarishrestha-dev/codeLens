import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

# API-level tests import the app via the `backend.app.*` package path
# (how uvicorn loads it). The parent directory must be importable.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import repository_store
from app.services.repository_store import (
    RepositoryFilesMissing,
    delete_repository,
    get_repository,
    list_repositories,
    reset_store,
    save_repository,
)


class RepositoryPersistenceTest(unittest.TestCase):
    """Workspace metadata survives a restart; analysis is rebuilt from files.

    The store persists a lightweight JSON index (id, name, path, timestamps)
    and intentionally does NOT persist analysis objects — those are rebuilt
    from the stored repository files on first access. These tests simulate a
    backend restart with reset_store() (clears the in-memory cache and the
    loaded index, forcing a disk re-read).
    """

    def setUp(self):
        self.data_dir = Path(tempfile.mkdtemp(prefix="codelens_store_"))
        self.addCleanup(shutil.rmtree, self.data_dir, ignore_errors=True)

        self._old_env = os.environ.get(repository_store.DATA_DIR_ENV)
        os.environ[repository_store.DATA_DIR_ENV] = str(self.data_dir)
        self.addCleanup(self._restore_env)

        reset_store()
        self.addCleanup(reset_store)

        self.repo_dir = Path(tempfile.mkdtemp(prefix="codelens_repo_"))
        self.addCleanup(shutil.rmtree, self.repo_dir, ignore_errors=True)
        (self.repo_dir / "main.py").write_text(
            "def run():\n    return 1\n", encoding="utf-8"
        )
        (self.repo_dir / "util.py").write_text(
            "def helper():\n    return 2\n", encoding="utf-8"
        )

    def _restore_env(self):
        if self._old_env is None:
            os.environ.pop(repository_store.DATA_DIR_ENV, None)
        else:
            os.environ[repository_store.DATA_DIR_ENV] = self._old_env

    def _index_file(self) -> Path:
        return self.data_dir / "repositories.json"

    def _seed(self, repo_path=None, name="demo"):
        repo_path = repo_path or self.repo_dir
        return save_repository(
            str(repo_path),
            name,
            tree={"name": name},
            code_analysis={
                "main.py": {
                    "functions": [{"name": "run", "line": 1}],
                    "classes": [],
                }
            },
            dependencies={"forward": {}, "backward": {}},
            call_graph={"main.py": []},
            entry_points=["main.py"],
            architecture={"directories": {}},
        )

    # ---- persistence / reloading ----

    def test_index_written_to_disk(self):
        repository_id = self._seed()

        self.assertTrue(self._index_file().exists())

        on_disk = json.loads(self._index_file().read_text(encoding="utf-8"))
        self.assertEqual(on_disk[repository_id]["name"], "demo")
        self.assertEqual(on_disk[repository_id]["path"], str(self.repo_dir))

    def test_restart_reloads_repository_from_files(self):
        repository_id = self._seed()

        # Simulate a backend restart: memory and loaded index are cleared,
        # the JSON file on disk remains.
        reset_store()

        self.assertEqual(len(list_repositories()), 1)
        self.assertEqual(list_repositories()[0]["repository_id"], repository_id)

        rebuilt = get_repository(repository_id)

        self.assertIsNotNone(rebuilt)
        self.assertEqual(rebuilt["name"], "demo")
        # Analysis was rebuilt from the real files on disk, not the stub
        # objects passed to save_repository.
        self.assertEqual(set(rebuilt["code_analysis"]), {"main.py", "util.py"})
        self.assertEqual(
            rebuilt["tree"]["name"], "demo",
            "display name must survive the restart",
        )

    def test_reanalysis_same_path_keeps_stable_id(self):
        first = self._seed()
        second = self._seed(name="demo-renamed")

        self.assertEqual(first, second, "same location must keep the same id")

        entry = list_repositories()[0]
        self.assertEqual(entry["name"], "demo-renamed")

    def test_list_sorted_most_recent_first(self):
        older = self.repo_dir / "older"
        newer = self.repo_dir / "newer"
        for directory in (older, newer):
            directory.mkdir()
            (directory / "main.py").write_text("x = 1\n", encoding="utf-8")

        first_id = self._seed(repo_path=older, name="older")
        second_id = self._seed(repo_path=newer, name="newer")

        ids = [entry["repository_id"] for entry in list_repositories()]
        self.assertEqual(ids, [second_id, first_id])

    # ---- missing directories ----

    def test_missing_directory_reported_not_usable(self):
        repository_id = self._seed()

        shutil.rmtree(self.repo_dir)

        entries = list_repositories()
        self.assertEqual(len(entries), 1)
        self.assertFalse(entries[0]["available"])
        # The entry is kept so the UI can offer removal of the stale record.

        with self.assertRaises(RepositoryFilesMissing):
            get_repository(repository_id)

    def test_missing_directory_after_restart(self):
        repository_id = self._seed()
        reset_store()

        shutil.rmtree(self.repo_dir)

        self.assertFalse(list_repositories()[0]["available"])

        with self.assertRaises(RepositoryFilesMissing):
            get_repository(repository_id)

    def test_directory_deleted_while_cached_in_memory(self):
        repository_id = self._seed()
        # Prime the in-memory cache.
        self.assertIsNotNone(get_repository(repository_id))

        shutil.rmtree(self.repo_dir)

        with self.assertRaises(RepositoryFilesMissing):
            get_repository(repository_id)

    def test_unknown_id_returns_none(self):
        self.assertIsNone(get_repository("does-not-exist"))
        self.assertEqual(list_repositories(), [])

    # ---- removal ----

    def test_delete_removes_index_entry_but_keeps_files(self):
        repository_id = self._seed()

        self.assertTrue(delete_repository(repository_id))

        self.assertEqual(list_repositories(), [])
        self.assertIsNone(get_repository(repository_id))
        self.assertTrue(
            self.repo_dir.exists(),
            "removal from CodeLens must never delete source files",
        )

        # Persisted: a restart does not resurrect the workspace.
        reset_store()
        self.assertEqual(list_repositories(), [])

    def test_delete_unknown_id_returns_false(self):
        self.assertFalse(delete_repository("does-not-exist"))

    def test_index_file_survives_corruption_gracefully(self):
        self._index_file().write_text("{not json", encoding="utf-8")
        reset_store()

        self.assertEqual(list_repositories(), [])

        # Store remains usable after a corrupt index.
        repository_id = self._seed()
        self.assertEqual(len(list_repositories()), 1)
        self.assertIsNotNone(get_repository(repository_id))


class RepositoryApiTest(unittest.TestCase):
    """End-to-end coverage of the workspace endpoints through the FastAPI app.

    Uses the `backend.app.*` import path (same as uvicorn). The env-var
    override keeps every test inside a temp data directory.
    """

    def setUp(self):
        from fastapi.testclient import TestClient
        from backend.app.main import app
        from backend.app.services import repository_store as api_store

        self.api_store = api_store
        self.data_dir = Path(tempfile.mkdtemp(prefix="codelens_api_"))
        self.addCleanup(shutil.rmtree, self.data_dir, ignore_errors=True)

        self._old_env = os.environ.get(api_store.DATA_DIR_ENV)
        os.environ[api_store.DATA_DIR_ENV] = str(self.data_dir)
        self.addCleanup(self._restore_env)

        api_store.reset_store()
        self.addCleanup(api_store.reset_store)

        self.client = TestClient(app)

        self.repo_dir = Path(tempfile.mkdtemp(prefix="codelens_api_repo_"))
        self.addCleanup(shutil.rmtree, self.repo_dir, ignore_errors=True)
        (self.repo_dir / "main.py").write_text(
            "def run():\n    return 1\n", encoding="utf-8"
        )

    def _restore_env(self):
        if self._old_env is None:
            os.environ.pop(self.api_store.DATA_DIR_ENV, None)
        else:
            os.environ[self.api_store.DATA_DIR_ENV] = self._old_env

    def _seed_via_store(self, name="demo"):
        repository_id = self.api_store.save_repository(
            str(self.repo_dir),
            name,
            tree={"name": name},
            code_analysis={"main.py": {"functions": [], "classes": []}},
            dependencies={"forward": {}, "backward": {}},
            call_graph={},
            entry_points=["main.py"],
            architecture={"directories": {}},
        )
        return repository_id

    def test_repositories_endpoint_lists_workspaces(self):
        repository_id = self._seed_via_store()

        response = self.client.get("/repositories")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body["repositories"]), 1)

        entry = body["repositories"][0]
        self.assertEqual(entry["repository_id"], repository_id)
        self.assertEqual(entry["name"], "demo")
        self.assertTrue(entry["available"])

    def test_repository_endpoint_rebuilds_after_restart(self):
        repository_id = self._seed_via_store()
        self.api_store.reset_store()

        response = self.client.get(f"/repository/{repository_id}")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["repository_id"], repository_id)
        self.assertEqual(body["name"], "demo")
        self.assertEqual(set(body["code_analysis"]), {"main.py"})

    def test_repository_endpoint_410_when_files_missing(self):
        repository_id = self._seed_via_store()

        shutil.rmtree(self.repo_dir)

        response = self.client.get(f"/repository/{repository_id}")

        self.assertEqual(response.status_code, 410)

    def test_repository_endpoint_404_for_unknown_id(self):
        response = self.client.get("/repository/nope")
        self.assertEqual(response.status_code, 404)

    def test_delete_repository_endpoint(self):
        repository_id = self._seed_via_store()

        response = self.client.delete(f"/repository/{repository_id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get("/repositories").json()["repositories"], [])
        # Files are preserved.
        self.assertTrue(self.repo_dir.exists())

    def test_delete_unknown_repository_404(self):
        response = self.client.delete("/repository/nope")
        self.assertEqual(response.status_code, 404)

    def test_file_endpoint_410_when_files_missing(self):
        repository_id = self._seed_via_store()

        shutil.rmtree(self.repo_dir)

        response = self.client.get(
            "/file",
            params={"repository_id": repository_id, "file_path": "main.py"},
        )

        self.assertEqual(response.status_code, 410)

    def test_analyze_zip_registers_workspace(self):
        # Full ingestion through the API: upload a real tiny zip.
        import io
        import zipfile

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("main.py", "def run():\n    return 1\n")

        response = self.client.post(
            "/analyze/zip",
            files={"file": ("tinyproj.zip", buffer.getvalue(), "application/zip")},
        )

        self.assertEqual(response.status_code, 200)
        repository_id = response.json()["repository_id"]

        listed = self.client.get("/repositories").json()["repositories"]
        self.assertIn(repository_id, [entry["repository_id"] for entry in listed])

        # And the workspace is fully usable through the repository endpoint.
        info = self.client.get(f"/repository/{repository_id}")
        self.assertEqual(info.status_code, 200)
        self.assertIn("main.py", info.json()["code_analysis"])

        # Clean up the extracted copy under the default data dir.
        listed = self.client.get("/repositories").json()["repositories"]
        entry = next(e for e in listed if e["repository_id"] == repository_id)
        self.addCleanup(shutil.rmtree, entry["path"], ignore_errors=True)
        self.client.delete(f"/repository/{repository_id}")


if __name__ == "__main__":
    unittest.main()

"""Focused tests for production CORS and storage path configuration."""

import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class CorsOriginsTest(unittest.TestCase):
    """CODELENS_CORS_ORIGINS parsing and defaults."""

    def setUp(self):
        # Import the helper without re-initialising the whole app when possible.
        from backend.app import main as main_module

        self.main = main_module
        self._old = os.environ.get("CODELENS_CORS_ORIGINS")

    def tearDown(self):
        if self._old is None:
            os.environ.pop("CODELENS_CORS_ORIGINS", None)
        else:
            os.environ["CODELENS_CORS_ORIGINS"] = self._old

    def test_default_when_unset(self):
        os.environ.pop("CODELENS_CORS_ORIGINS", None)
        origins = self.main._parse_cors_origins(
            os.environ.get("CODELENS_CORS_ORIGINS", self.main._DEFAULT_CORS_ORIGINS)
        )
        self.assertEqual(origins, ["http://localhost:5173"])

    def test_comma_separated_trimmed(self):
        raw = " https://a.example.com , http://localhost:5173 ,, "
        origins = self.main._parse_cors_origins(raw)
        self.assertEqual(
            origins, ["https://a.example.com", "http://localhost:5173"]
        )

    def test_empty_falls_back_to_default(self):
        self.assertEqual(
            self.main._parse_cors_origins("  ,  , "),
            ["http://localhost:5173"],
        )

    def test_no_wildcard_accepted_as_literal(self):
        # Wildcards are not special-cased; an operator who sets "*" gets "*"
        # as a single origin (Starlette will treat it per its own rules).
        self.assertEqual(self.main._parse_cors_origins("*"), ["*"])


class StoragePathTest(unittest.TestCase):
    """CODELENS_DATA_DIR resolution and safe directory creation."""

    def setUp(self):
        from backend.app.services import repository_store

        self.store = repository_store
        self._old = os.environ.get(repository_store.DATA_DIR_ENV)
        self._tmp = Path(tempfile.mkdtemp(prefix="codelens_storage_"))

    def tearDown(self):
        import shutil

        if self._old is None:
            os.environ.pop(self.store.DATA_DIR_ENV, None)
        else:
            os.environ[self.store.DATA_DIR_ENV] = self._old
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_default_windows_path_preserved(self):
        os.environ.pop(self.store.DATA_DIR_ENV, None)
        self.assertEqual(self.store.data_dir(), Path("E:/CodeLensData"))

    def test_linux_style_path_accepted(self):
        target = self._tmp / "data" / "codelens"
        os.environ[self.store.DATA_DIR_ENV] = str(target)
        self.assertEqual(self.store.data_dir(), Path(str(target)))

    def test_index_write_creates_directory(self):
        target = self._tmp / "nested" / "codelens"
        os.environ[self.store.DATA_DIR_ENV] = str(target)
        self.assertFalse(target.exists())

        self.store.reset_store()
        try:
            # _write_index must mkdir parents before writing repositories.json.
            self.store._load_index()
            self.store._write_index()
            self.assertTrue(target.is_dir())
            self.assertTrue((target / "repositories.json").is_file())
        finally:
            self.store.reset_store()

    def test_ingestion_paths_use_data_dir(self):
        """github/zip helpers and analyze_zip must not hardcode E:/CodeLensData."""
        import inspect

        from backend.app.services import github_service, zip_service
        from backend.app import main as main_module

        for fn in (github_service.clone_repository, zip_service.extract_zip):
            source = inspect.getsource(fn)
            self.assertNotIn("E:/CodeLensData", source)

        analyze_zip_src = inspect.getsource(main_module.analyze_zip)
        self.assertNotIn("E:/CodeLensData", analyze_zip_src)
        self.assertIn("data_dir()", analyze_zip_src)


if __name__ == "__main__":
    unittest.main()

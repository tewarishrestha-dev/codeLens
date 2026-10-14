import shutil
import tempfile
import unittest
from pathlib import Path

from app.services.repository_parser import parse_repository
from app.services.dependency_analyzer import build_dependencies
from app.services.call_analyzer import build_call_graph


class RepositoryParserPathNormalizationTest(unittest.TestCase):
    """Repository-relative keys must use forward slashes on every platform.

    Windows ``str(Path(...))`` yields backslashes, which broke frontend
    ``code_analysis`` lookups and execution-flow entry-point round-trips.
    Every consumer (dependencies, call graph) inherits the parser's keys, so
    normalizing at the source fixes them all.
    """

    def setUp(self):
        self.repo = Path(tempfile.mkdtemp())
        pkg = self.repo / "pkg"
        pkg.mkdir()
        (pkg / "util.py").write_text(
            "def helper():\n    return 1\n", encoding="utf-8"
        )
        (pkg / "main.py").write_text(
            "from pkg import util\n\n\ndef run():\n    return util.helper()\n",
            encoding="utf-8",
        )

    def tearDown(self):
        shutil.rmtree(self.repo, ignore_errors=True)

    def test_parser_keys_use_forward_slashes(self):
        result = parse_repository(self.repo)

        self.assertEqual(set(result), {"pkg/main.py", "pkg/util.py"})

    def test_dependencies_keys_use_forward_slashes(self):
        dependencies = build_dependencies(parse_repository(self.repo))

        self.assertEqual(
            set(dependencies["forward"]), {"pkg/main.py", "pkg/util.py"}
        )
        self.assertEqual(set(dependencies["reverse"]), {"pkg/main.py", "pkg/util.py"})

    def test_call_graph_keys_use_forward_slashes(self):
        call_graph = build_call_graph(parse_repository(self.repo))

        self.assertEqual(set(call_graph), {"pkg/main.py", "pkg/util.py"})

    def test_no_key_contains_a_backslash(self):
        for key in parse_repository(self.repo):
            self.assertNotIn("\\", key)


if __name__ == "__main__":
    unittest.main()

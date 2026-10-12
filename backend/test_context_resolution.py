import shutil
import tempfile
import unittest
from pathlib import Path

from app.services.repository_parser import parse_repository
from app.services.call_analyzer import (
    build_call_graph,
    build_execution_flow,
    resolve_call_targets,
)
from app.services.code_search import search_code
from app.services.context_builder import (
    build_context,
    get_function_source,
)


class ContextResolutionTest(unittest.TestCase):
    def make_repo(self, files):
        directory = tempfile.mkdtemp(prefix="codelens_batch1_")
        self.addCleanup(shutil.rmtree, directory, ignore_errors=True)

        for name, content in files.items():
            path = Path(directory) / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

        return Path(directory)

    def analyze(self, files, query):
        repo_path = self.make_repo(files)
        code_analysis = parse_repository(repo_path)
        call_graph = build_call_graph(code_analysis)
        search_results = search_code(code_analysis, query)
        context = build_context(
            repo_path, code_analysis, search_results, call_graph
        )
        return code_analysis, call_graph, context

    def collect_code(self, context):
        entries = []
        for item in context:
            entries.extend(item["code"])
        return entries

    def test_resolve_call_targets_supports_new_and_legacy_shapes(self):
        self.assertEqual(resolve_call_targets({}), [])

        legacy_single = {
            "calls": "helper",
            "target_file": "a.py",
            "target_line": 3,
        }
        self.assertEqual(
            resolve_call_targets(legacy_single),
            [("a.py", 3)],
        )

        legacy_many = {
            "calls": "helper",
            "target_file": ["a.py", "b.py"],
            "target_line": [1, 2],
        }
        self.assertEqual(
            resolve_call_targets(legacy_many),
            [("a.py", 1), ("b.py", 2)],
        )

    def test_call_graph_marks_unique_and_ambiguous_targets(self):
        files = {
            "a.py": "def shared():\n    return 1\n",
            "b.py": "def shared():\n    return 2\n",
            "c.py": "def entry():\n    return shared()\n",
        }
        repo_path = self.make_repo(files)
        code_analysis = parse_repository(repo_path)
        graph = build_call_graph(code_analysis)

        ambiguous = graph["c.py"]["entry"][0]
        self.assertTrue(ambiguous["ambiguous"])
        self.assertEqual(len(ambiguous["target_file"]), 2)
        self.assertEqual(len(ambiguous["targets"]), 2)

        unique_files = {
            "u.py": "def helper():\n    return 1\n",
            "v.py": "def caller():\n    return helper()\n",
        }
        repo_path = self.make_repo(unique_files)
        code_analysis = parse_repository(repo_path)
        graph = build_call_graph(code_analysis)

        unique = graph["v.py"]["caller"][0]
        self.assertFalse(unique["ambiguous"])
        self.assertEqual(unique["target_file"], "u.py")
        self.assertEqual(unique["targets"], [{"file": "u.py", "line": 1}])

    def test_context_resolves_method_call_target(self):
        files = {
            "main.py": (
                "def process():\n"
                "    return Engine().compute(2)\n"
                "\n"
                "\n"
                "class Engine:\n"
                "    def compute(self, value):\n"
                "        return value + 1\n"
                "\n"
                "    def other(self):\n"
                "        return 0\n"
            ),
        }
        _, _, context = self.analyze(files, "process")

        entries = self.collect_code(context)
        names = {entry["name"] for entry in entries}

        self.assertIn("process", names)
        self.assertIn("compute", names)

        compute = next(entry for entry in entries if entry["name"] == "compute")
        self.assertEqual(compute["file"], "main.py")
        self.assertIn("def compute", compute["source"])
        self.assertNotIn("def other", compute["source"])

    def test_context_keeps_all_candidates_for_ambiguous_name(self):
        files = {
            "a.py": "def shared():\n    return 1\n",
            "b.py": "def shared():\n    return 2\n",
            "c.py": "def entry():\n    return shared()\n",
        }
        _, _, context = self.analyze(files, "entry")

        entries = self.collect_code(context)
        shared_files = {
            entry["file"]
            for entry in entries
            if entry["name"] == "shared"
        }

        self.assertEqual(shared_files, {"a.py", "b.py"})

    def test_context_resolves_unique_target(self):
        files = {
            "u.py": "def helper():\n    return 1\n",
            "v.py": "def caller():\n    return helper()\n",
        }
        _, _, context = self.analyze(files, "caller")

        entries = self.collect_code(context)
        self.assertIn(
            ("helper", "u.py"),
            {(entry["name"], entry["file"]) for entry in entries},
        )

    def test_execution_flow_follows_ambiguous_candidates(self):
        files = {
            "a.py": "def shared():\n    return 1\n",
            "b.py": "def shared():\n    return 2\n",
            "c.py": "def entry():\n    return shared()\n",
        }
        repo_path = self.make_repo(files)
        code_analysis = parse_repository(repo_path)
        graph = build_call_graph(code_analysis)

        flow = build_execution_flow(graph, "c.py")
        shared_files = {
            step["file"]
            for step in flow
            if step["function"] == "shared"
        }

        self.assertEqual(shared_files, {"a.py", "b.py"})

    def test_execution_flow_follows_unique_target(self):
        files = {
            "u.py": "def helper():\n    return 1\n",
            "v.py": "def caller():\n    return helper()\n",
        }
        repo_path = self.make_repo(files)
        code_analysis = parse_repository(repo_path)
        graph = build_call_graph(code_analysis)

        flow = build_execution_flow(graph, "v.py")
        self.assertIn(
            ("u.py", "helper"),
            {(step["file"], step["function"]) for step in flow},
        )

    def test_get_function_source_stops_at_dedent(self):
        source = (
            "def a():\n"
            "    x = 1\n"
            "\n"
            "\n"
            "def b():\n"
            "    return 2\n"
        )
        extracted = get_function_source(source, {"line": 1})
        self.assertIn("def a", extracted)
        self.assertNotIn("def b", extracted)


if __name__ == "__main__":
    unittest.main()

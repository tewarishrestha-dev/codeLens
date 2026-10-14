import shutil
import tempfile
import unittest
from pathlib import Path

from app.services.repository_parser import parse_repository
from app.services.call_analyzer import build_call_graph
from app.services.code_search import search_code
from app.services import context_builder
from app.services.context_builder import build_context


CORE = (
    "class Context:\n"
    "    def invoke(self, callback):\n"
    "        \"\"\"Invokes a command callback in the way it expects.\"\"\"\n"
    "        return callback()\n"
    "\n"
    "\n"
    "class Command:\n"
    "    def invoke(self, ctx):\n"
    "        \"\"\"Given a context, this invokes the attached command callback.\"\"\"\n"
    "        return ctx.invoke(self.callback)\n"
    "\n"
    "    def main(self, args):\n"
    "        \"\"\"Runs command execution for the command line application.\"\"\"\n"
    "        return self.invoke(args)\n"
    "\n"
    "\n"
    "class Group(Command):\n"
    "    def invoke(self, ctx):\n"
    "        \"\"\"Dispatches the selected subcommand to its command callback.\"\"\"\n"
    "        return self.run_subcommand(ctx)\n"
)

IMAGEPIPE = (
    "def process_commands(processors):\n"
    "    \"\"\"Composes chained command processors into a pipeline and drains it.\"\"\"\n"
    "    stream = ()\n"
    "    for processor in processors:\n"
    "        stream = processor(stream)\n"
    "    for _ in stream:\n"
    "        pass\n"
)

DECOY = (
    "def command():\n"
    "    \"\"\"A command definition that does not execute anything.\"\"\"\n"
    "    return None\n"
)

FILLER = (
    "def handle_command(request):\n"
    "    \"\"\"Handles a command request and returns the command result.\"\"\"\n"
    "    return request\n"
    "\n"
    "\n"
    "def run_command(request):\n"
    "    \"\"\"Runs a command and returns the command result.\"\"\"\n"
    "    return request\n"
)

QUERY = "Where is command execution implemented?"


def normalize(path):
    return path.replace("\\", "/")


class SearchRetrievalTest(unittest.TestCase):
    def make_repo(self, files):
        directory = tempfile.mkdtemp(prefix="codelens_batch2_")
        self.addCleanup(shutil.rmtree, directory, ignore_errors=True)

        for name, content in files.items():
            path = Path(directory) / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

        return Path(directory)

    def fixture(self):
        files = {
            "src/core.py": CORE,
            "examples/imagepipe/imagepipe.py": IMAGEPIPE,
            "src/decoy.py": DECOY,
        }

        for index in range(1, 5):
            files[f"fillers/f{index}.py"] = FILLER

        return files

    def test_body_search_finds_function_without_name_match(self):
        repo_path = self.make_repo({
            "svc.py": (
                "def dispatch(handler):\n"
                "    \"\"\"Performs command execution for the given handler.\"\"\"\n"
                "    return handler()\n"
            ),
        })
        code_analysis = parse_repository(repo_path)

        with_path = search_code(code_analysis, QUERY, repo_path)
        names = {
            (match["name"], match.get("reason"))
            for result in with_path
            for match in result["matches"]
        }
        self.assertIn(("dispatch", "body"), names)

        without_path = search_code(code_analysis, QUERY)
        self.assertEqual(without_path, [])

    def test_query_ranks_dispatch_core_above_example(self):
        repo_path = self.make_repo(self.fixture())
        code_analysis = parse_repository(repo_path)

        results = search_code(code_analysis, QUERY, repo_path)
        ranked = [normalize(result["file"]) for result in results]

        self.assertEqual(ranked[0], "src/core.py")

        core = next(r for r in results if normalize(r["file"]) == "src/core.py")
        reasons = {(match["name"], match.get("reason")) for match in core["matches"]}
        self.assertIn(("invoke", "body"), reasons)
        self.assertIn(("main", "body"), reasons)

        scores = {normalize(r["file"]): r["score"] for r in results}
        self.assertGreater(scores["src/core.py"], scores["examples/imagepipe/imagepipe.py"])

        example_rank = ranked.index("examples/imagepipe/imagepipe.py")
        self.assertGreaterEqual(example_rank, context_builder.MAX_CONTEXT_FILES)

    def test_context_includes_dispatch_and_excludes_process_commands(self):
        repo_path = self.make_repo(self.fixture())
        code_analysis = parse_repository(repo_path)
        call_graph = build_call_graph(code_analysis)

        search_results = search_code(code_analysis, QUERY, repo_path)
        context = build_context(repo_path, code_analysis, search_results, call_graph)

        context_files = [normalize(item["file"]) for item in context]
        self.assertIn("src/core.py", context_files)
        self.assertNotIn("examples/imagepipe/imagepipe.py", context_files)

        core = next(
            item for item in context if normalize(item["file"]) == "src/core.py"
        )
        names = {entry["name"] for entry in core["code"]}

        self.assertIn("invoke", names)
        self.assertIn("main", names)

        all_names = {
            entry["name"]
            for item in context
            for entry in item["code"]
        }
        self.assertNotIn("process_commands", all_names)

    def test_identifier_only_search_when_no_repo_path(self):
        repo_path = self.make_repo({
            "svc.py": (
                "def process_commands(processors):\n"
                '    """Composes subcommands into a pipeline."""\n'
                "    return processors\n"
            ),
        })
        code_analysis = parse_repository(repo_path)

        results = search_code(code_analysis, "commander", None)
        self.assertEqual(results, [])

    def test_test_files_do_not_crowd_out_source(self):
        """Keyword-rich test files rank below real source matches."""
        repo_path = self.make_repo({
            "src/core.py": CORE,
            "tests/test_command_execution.py": (
                "def test_command_execution():\n"
                '    """Tests command execution flow."""\n'
                "    run_command()\n"
                "    handle_command()\n"
            ),
        })
        code_analysis = parse_repository(repo_path)

        results = search_code(code_analysis, QUERY, repo_path)
        ranked = [normalize(result["file"]) for result in results]

        # Real source outranks the keyword-rich test file even though the
        # test file mentions the same query keywords.
        self.assertIn("src/core.py", ranked)
        self.assertIn("tests/test_command_execution.py", ranked)
        self.assertLess(
            ranked.index("src/core.py"),
            ranked.index("tests/test_command_execution.py"),
        )


if __name__ == "__main__":
    unittest.main()

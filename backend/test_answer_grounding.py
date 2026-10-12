import shutil
import tempfile
import unittest
from pathlib import Path

from app.services.repository_parser import parse_repository
from app.services.call_analyzer import build_call_graph
from app.services.code_search import search_code
from app.services import context_builder
from app.services.context_builder import build_context
from app.services.llm_service import build_prompt, validate_citations


DECOYS = "\n\n".join(
    f"def helper_{index}():\n"
    f"    \"\"\"command execution helper {index}.\"\"\"\n"
    f"    return {index}"
    for index in range(50)
)

CLASSES = (
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

CORE = DECOYS + "\n\n\n" + CLASSES

IMAGEPIPE = (
    "def process_commands(processors):\n"
    "    \"\"\"Chains command streams produced by subcommands and drains them.\"\"\"\n"
    "    stream = ()\n"
    "    for processor in processors:\n"
    "        stream = processor(stream)\n"
    "    for _ in stream:\n"
    "        pass\n"
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

Q1 = (
    "Where is command execution implemented? Explain the execution flow and "
    "cite the exact source lines."
)
Q2 = (
    "What does process_commands in examples/imagepipe/imagepipe.py do? Explain "
    "its purpose and distinguish it from Click's command-dispatch mechanism."
)
Q2_WITHOUT_PATH = "What does process_commands do? Explain its purpose."


def normalize(path):
    return path.replace("\\", "/")


class AnswerGroundingTest(unittest.TestCase):
    def make_repo(self, files):
        directory = tempfile.mkdtemp(prefix="codelens_grounding_")
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
        }

        for index in range(1, 7):
            files[f"fillers/f{index}.py"] = FILLER

        return files

    def analyze(self, query):
        repo_path = self.make_repo(self.fixture())
        code_analysis = parse_repository(repo_path)
        call_graph = build_call_graph(code_analysis)
        search_results = search_code(code_analysis, query, repo_path)
        context = build_context(repo_path, code_analysis, search_results, call_graph)
        return search_results, context

    def test_named_repository_path_is_ranked_first(self):
        results, _ = self.analyze(Q2)
        top = results[0]

        self.assertTrue(top["named"])
        self.assertEqual(normalize(top["file"]), "examples/imagepipe/imagepipe.py")
        self.assertIn(
            "examples/imagepipe/imagepipe.py",
            [normalize(r["file"]) for r in results[:context_builder.MAX_CONTEXT_FILES]],
        )

    def test_named_boost_only_applies_with_explicit_path(self):
        results, _ = self.analyze(Q2_WITHOUT_PATH)
        self.assertFalse(any(result["named"] for result in results))

    def test_q2_context_contains_process_commands_body(self):
        _, context = self.analyze(Q2)

        imagepipe = next(
            (
                item
                for item in context
                if normalize(item["file"]) == "examples/imagepipe/imagepipe.py"
            ),
            None,
        )
        self.assertIsNotNone(imagepipe)

        entry = next(
            code for code in imagepipe["code"] if code["name"] == "process_commands"
        )

        self.assertIn("stream = ()", entry["source"])
        self.assertIn("stream = processor(stream)", entry["source"])
        self.assertNotIn("open(", entry["source"])
        self.assertNotIn("read(", entry["source"])
        self.assertNotIn("parse", entry["source"].lower())

    def test_q1_context_includes_dispatch_functions(self):
        _, context = self.analyze(Q1)

        core = next(
            (item for item in context if normalize(item["file"]) == "src/core.py"),
            None,
        )
        self.assertIsNotNone(core)

        names = [code["name"] for code in core["code"]]
        self.assertIn("Command", names)
        self.assertIn("invoke", names)
        self.assertIn("main", names)

        main_entry = next(code for code in core["code"] if code["name"] == "main")
        self.assertIn("command execution", main_entry["source"])

    def test_function_ranking_prefers_named_over_line(self):
        results, _ = self.analyze(Q1)
        core = next(
            r for r in results if normalize(r["file"]) == "src/core.py"
        )
        matches = core["matches"]

        self.assertEqual(matches[0]["name"], "Command")
        self.assertEqual(matches[0]["reason"], "name")

        invoke_index = next(
            i for i, m in enumerate(matches) if m["name"] == "invoke"
        )
        helper_index = next(
            i for i, m in enumerate(matches) if m["name"] == "helper_0"
        )
        self.assertLess(invoke_index, helper_index)

    def test_prompt_states_grounding_rules(self):
        _, context = self.analyze(Q2)
        prompt = build_prompt(Q2, context)

        self.assertIn("Do not rely on prior knowledge", prompt)
        self.assertIn("does not contain it", prompt)
        self.assertIn(Q2, prompt)

    def test_valid_citation_is_preserved(self):
        context = [{
            "file": "a.py",
            "code": [{"name": "f", "line": 1, "source": "1: def f():\n2:     return 1"}],
            "matches": [],
            "imports": [],
        }]

        answer = validate_citations("See [a.py:2].", context)
        self.assertIn("[a.py:2]", answer)
        self.assertNotIn("unverified", answer.lower())

    def test_unverified_citation_is_reported_not_removed(self):
        context = [{
            "file": "a.py",
            "code": [{"name": "f", "line": 1, "source": "1: def f():\n2:     return 1"}],
            "matches": [],
            "imports": [],
        }]

        answer = validate_citations("Uses [a.py:2] but also [a.py:99].", context)

        self.assertIn("[a.py:2]", answer)
        self.assertIn("a.py:99", answer)
        self.assertIn("unverified", answer.lower())
        self.assertIn("Note:", answer)

    def test_citation_note_does_not_claim_semantic_validation(self):
        context = [{
            "file": "a.py",
            "code": [{"name": "f", "line": 1, "source": "1: def f():\n2:     return 1"}],
            "matches": [],
            "imports": [],
        }]

        answer = validate_citations("Only [a.py:7].", context)

        lowered = answer.lower()
        self.assertIn("not found in the retrieved source", lowered)
        self.assertNotIn("source supports", lowered)
        self.assertNotIn("does not support the claim", lowered)


if __name__ == "__main__":
    unittest.main()

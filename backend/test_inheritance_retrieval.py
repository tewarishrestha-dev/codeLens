import shutil
import tempfile
import unittest
from pathlib import Path

from app.services.code_parser import parse_python_file
from app.services.repository_parser import parse_repository
from app.services.call_analyzer import build_call_graph
from app.services.code_search import search_code
from app.services.context_builder import build_context


CORE = (
    "class Command:\n"
    "    def invoke(self, ctx):\n"
    '        """Given a context, this invokes the attached command callback."""\n'
    "        return ctx.invoke(self.callback)\n"
    "\n"
    "    def main(self, args):\n"
    '        """Runs command execution."""\n'
    "        return self.invoke(args)\n"
    "\n"
    "\n"
    "class Group(Command):\n"
    "    def invoke(self, ctx):\n"
    '        """Dispatches the selected subcommand to its callback."""\n'
    "        return self.run(ctx)\n"
    "\n"
    "    def run(self, ctx):\n"
    "        return ctx\n"
    "\n"
    "\n"
    "class Widget:\n"
    "    def invoke(self, ctx):\n"
    '        """Renders the widget."""\n'
    "        return ctx\n"
    "\n"
    "\n"
    "def serialize(payload):\n"
    '    """Serializes the payload."""\n'
    "    return payload\n"
)

# Names the class ``Command``; its subclass ``Group.invoke`` has no query
# keywords in its body or docstring, so it can only be retrieved via parsed
# inheritance.
QUERY = "Where is command dispatch implemented?"

# Names no class, so inheritance expansion must stay disabled.
GENERIC_QUERY = "serialize payload"

# Two modules define unrelated classes named ``Command``. The query names
# only ``src/alpha.py``, so only that module's hierarchy may expand.
ALPHA = (
    "class Command:\n"
    "    def invoke(self, ctx):\n"
    '        """Given a context, this invokes the attached command callback."""\n'
    "        return ctx.invoke(self.callback)\n"
    "\n"
    "\n"
    "class AlphaGroup(Command):\n"
    "    def invoke(self, ctx):\n"
    '        """Dispatches the selected subcommand to its callback."""\n'
    "        return self.run(ctx)\n"
    "\n"
    "    def run(self, ctx):\n"
    "        return ctx\n"
)

BETA = (
    "class Command:\n"
    "    def invoke(self, ctx):\n"
    '        """Given a context, this invokes the attached command callback."""\n'
    "        return ctx.invoke(self.callback)\n"
    "\n"
    "\n"
    "class BetaGroup(Command):\n"
    "    def invoke(self, ctx):\n"
    '        """Dispatches the selected subcommand to its callback."""\n'
    "        return self.run(ctx)\n"
    "\n"
    "    def run(self, ctx):\n"
    "        return ctx\n"
)

CROSS_MODULE_QUERY = (
    "Where is command dispatch implemented in src/alpha.py?"
)


def normalize(path):
    return path.replace("\\", "/")


class InheritanceRetrievalTest(unittest.TestCase):
    def make_repo(self, files):
        directory = tempfile.mkdtemp(prefix="codelens_inherit_")
        self.addCleanup(shutil.rmtree, directory, ignore_errors=True)

        for name, content in files.items():
            path = Path(directory) / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

        return Path(directory)

    def core_data(self, code_analysis):
        key = next(
            path
            for path in code_analysis
            if normalize(path) == "src/core.py"
        )
        return code_analysis[key]

    def core_result(self, results):
        return next(
            result
            for result in results
            if normalize(result["file"]) == "src/core.py"
        )

    def test_parser_records_base_classes(self):
        directory = Path(tempfile.mkdtemp(prefix="codelens_parser_"))
        self.addCleanup(shutil.rmtree, directory, ignore_errors=True)
        target = directory / "shapes.py"
        target.write_text(
            "class Command:\n"
            "    pass\n"
            "\n"
            "\n"
            "class Group(Command):\n"
            "    pass\n"
            "\n"
            "\n"
            "class Qualified(cli.Command):\n"
            "    pass\n"
            "\n"
            "\n"
            "class Generic(abc.Mapping[str, int]):\n"
            "    pass\n",
            encoding="utf-8",
        )

        result = parse_python_file(target)
        bases = {cls["name"]: cls["bases"] for cls in result["classes"]}

        self.assertEqual(bases["Command"], [])
        self.assertEqual(bases["Group"], ["Command"])
        self.assertEqual(bases["Qualified"], ["Command"])
        self.assertEqual(bases["Generic"], ["Mapping"])

    def test_command_query_retrieves_subclass_invoke(self):
        repo_path = self.make_repo({"src/core.py": CORE})
        code_analysis = parse_repository(repo_path)

        group = next(
            cls
            for cls in self.core_data(code_analysis)["classes"]
            if cls["name"] == "Group"
        )
        self.assertEqual(group["bases"], ["Command"])

        results = search_code(code_analysis, QUERY, repo_path)
        core = self.core_result(results)

        inherited = {
            (match.get("class"), match["name"])
            for match in core["matches"]
            if match.get("reason") == "inherited"
        }
        self.assertIn(("Group", "invoke"), inherited)

    def test_group_invoke_appears_in_context(self):
        repo_path = self.make_repo({"src/core.py": CORE})
        code_analysis = parse_repository(repo_path)
        call_graph = build_call_graph(code_analysis)

        results = search_code(code_analysis, QUERY, repo_path)
        context = build_context(repo_path, code_analysis, results, call_graph)

        core = next(
            item
            for item in context
            if normalize(item["file"]) == "src/core.py"
        )
        sources = [entry["source"] for entry in core["code"]]

        self.assertTrue(
            any(
                "Dispatches the selected subcommand" in source
                for source in sources
            )
        )

    def test_unrelated_widget_invoke_not_promoted(self):
        repo_path = self.make_repo({"src/core.py": CORE})
        code_analysis = parse_repository(repo_path)

        results = search_code(code_analysis, QUERY, repo_path)
        core = self.core_result(results)

        self.assertFalse(
            any(match.get("class") == "Widget" for match in core["matches"])
        )

    def test_generic_query_does_not_expand_inheritance(self):
        repo_path = self.make_repo({"src/core.py": CORE})
        code_analysis = parse_repository(repo_path)

        results = search_code(code_analysis, GENERIC_QUERY, repo_path)

        reasons = {
            match.get("reason")
            for result in results
            for match in result["matches"]
        }
        self.assertNotIn("inherited", reasons)

    def test_same_name_subclass_not_promoted_across_modules(self):
        repo_path = self.make_repo({
            "src/alpha.py": ALPHA,
            "src/beta.py": BETA,
        })
        code_analysis = parse_repository(repo_path)

        results = search_code(code_analysis, CROSS_MODULE_QUERY, repo_path)

        alpha = next(
            result
            for result in results
            if normalize(result["file"]) == "src/alpha.py"
        )
        beta = next(
            result
            for result in results
            if normalize(result["file"]) == "src/beta.py"
        )

        # The named module's subclass is still promoted.
        alpha_inherited = {
            (match.get("class"), match["name"])
            for match in alpha["matches"]
            if match.get("reason") == "inherited"
        }
        self.assertIn(("AlphaGroup", "invoke"), alpha_inherited)

        # The other module's same-named hierarchy is not.
        beta_inherited = {
            (match.get("class"), match["name"])
            for match in beta["matches"]
            if match.get("reason") == "inherited"
        }
        self.assertEqual(beta_inherited, set())


if __name__ == "__main__":
    unittest.main()

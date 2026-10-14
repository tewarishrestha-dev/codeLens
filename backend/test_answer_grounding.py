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
        self.assertIn("not part of the answer", answer.lower())

    def test_citation_note_does_not_claim_semantic_validation(self):
        context = [{
            "file": "a.py",
            "code": [{"name": "f", "line": 1, "source": "1: def f():\n2:     return 1"}],
            "matches": [],
            "imports": [],
        }]

        answer = validate_citations("Only [a.py:7].", context)

        lowered = answer.lower()
        self.assertIn("does not support a confident answer", lowered)
        self.assertNotIn("source supports", lowered)
        self.assertNotIn("verified by semantic", lowered)

    def test_invented_behavior_citing_real_line_is_flagged(self):
        """A claim naming an identifier absent from its cited line is flagged."""
        context = [{
            "file": "a.py",
            "code": [{
                "name": "helper",
                "line": 5,
                "source": "5: def helper():\n6:     return 1",
            }],
            "matches": [],
            "imports": [],
        }]

        # The cited line (a.py:5) is retrieved and real, but it defines
        # `helper`, not `process_commands`. The claim invents behavior about
        # process_commands and must be flagged as unsupported.
        answer = validate_citations(
            "process_commands executes command definitions sequentially "
            "and handles errors [a.py:5].",
            context,
        )

        lowered = answer.lower()
        self.assertIn("not established by the retrieved source", lowered)
        self.assertIn("a.py:5", answer)

    def test_supported_claim_citing_containing_line_is_not_flagged(self):
        """A claim whose identifier appears on the cited line passes."""
        context = [{
            "file": "a.py",
            "code": [{
                "name": "process_commands",
                "line": 10,
                "source": (
                    "10: def process_commands(processors):\n"
                    "11:     for p in processors:\n"
                    "12:         p()"
                ),
            }],
            "matches": [],
            "imports": [],
        }]

        answer = validate_citations(
            "process_commands iterates the processors and calls each one "
            "[a.py:11].",
            context,
        )

        lowered = answer.lower()
        self.assertNotIn("not established by the retrieved source", lowered)
        self.assertIn("process_commands iterates", answer)

    def test_citation_path_words_are_not_treated_as_identifiers(self):
        """A filename inside [path:line] is not a claim identifier.

        Strips citation spans before the support check so a grounded claim
        like "defined on line [calculator.py:1]" is not flagged merely
        because the cited file's own name is absent from the snippet.
        """
        context = [{
            "file": "calculator.py",
            "code": [{
                "name": "add",
                "line": 1,
                "source": "1: def add(a, b):\n2:     return a + b",
            }],
            "matches": [],
            "imports": [],
        }]

        answer = validate_citations(
            "It is defined on line [calculator.py:1].",
            context,
        )

        lowered = answer.lower()
        self.assertNotIn("not established by the retrieved source", lowered)
        self.assertIn("defined on line", answer)

    def test_generic_prose_without_identifiers_is_not_flagged(self):
        """Claims with no distinctive identifiers are left alone."""
        context = [{
            "file": "a.py",
            "code": [{"name": "f", "line": 1, "source": "1: def f():\n2:     return 1"}],
            "matches": [],
            "imports": [],
        }]

        answer = validate_citations(
            "This function returns the value [a.py:2].",
            context,
        )

        lowered = answer.lower()
        self.assertNotIn("does not contain the identifiers", lowered)

    def test_valid_citation_still_preserved_after_semantic_check(self):
        """The new spot-check must not disturb valid citations."""
        context = [{
            "file": "a.py",
            "code": [{
                "name": "process_commands",
                "line": 10,
                "source": "10: def process_commands(processors):\n11:     return processors",
            }],
            "matches": [],
            "imports": [],
        }]

        answer = validate_citations("See [a.py:10].", context)
        self.assertIn("[a.py:10]", answer)
        self.assertNotIn("unverified", answer.lower())
        self.assertNotIn("may overstate", answer.lower())

    def test_suffix_path_citation_is_accepted(self):
        """A repo-relative suffix citation resolves to a retrieved file."""
        context = [{
            "file": "src/click/core.py",
            "code": [{
                "name": "invoke",
                "line": 100,
                "source": "100:     def invoke(self, ctx):\n101:         return ctx",
            }],
            "matches": [],
            "imports": [],
        }]

        for cited in ["click/core.py", "core.py", "src/click/core.py"]:
            answer = validate_citations(f"See [{cited}:101].", context)
            self.assertNotIn(
                "unverified", answer.lower(),
                msg=f"citation {cited} should resolve to src/click/core.py",
            )

    def test_fabricated_path_citation_is_flagged(self):
        """A citation naming a file that was not retrieved stays unverified."""
        context = [{
            "file": "src/click/core.py",
            "code": [{
                "name": "invoke",
                "line": 100,
                "source": "100:     def invoke(self, ctx):\n101:         return ctx",
            }],
            "matches": [],
            "imports": [],
        }]

        answer = validate_citations("See [click/arguments.py:696].", context)
        self.assertIn("unverified", answer.lower())
        self.assertIn("not part of the answer", answer.lower())

    def test_symbol_citation_resolves_to_real_file(self):
        """A ``func:line`` citation is rewritten to the retrieved file."""
        context = [{
            "file": "src/click/types.py",
            "code": [{
                "name": "launch",
                "line": 923,
                "source": "923: def launch(url):\n924:     return url",
            }],
            "matches": [],
            "imports": [],
        }]

        answer = validate_citations(
            "Click can launch a URL [launch:923].",
            context,
        )

        self.assertIn("src/click/types.py:923", answer)
        self.assertNotIn("unverified", answer.lower())

    def test_extensionless_path_citation_is_accepted(self):
        """A citation that drops the file extension still resolves."""
        context = [{
            "file": "src/click/core.py",
            "code": [{
                "name": "invoke",
                "line": 100,
                "source": "100:     def invoke(self, ctx):\n101:         return ctx",
            }],
            "matches": [],
            "imports": [],
        }]

        answer = validate_citations("See [click/core:100].", context)
        self.assertNotIn("unverified", answer.lower())

    def test_prompt_requires_verbatim_file_path_citations(self):
        """Prompt must forbid inventing/shortening citation file paths."""
        context = [{
            "file": "src/click/core.py",
            "code": [{
                "name": "invoke",
                "line": 100,
                "source": "100:     def invoke(self, ctx):\n101:         return ctx",
            }],
            "matches": [],
            "imports": [],
        }]

        prompt = build_prompt("Where is invoke?", context)
        self.assertIn("copied verbatim", prompt)
        self.assertIn("File: src/click/core.py", prompt)

    def test_mixed_answer_keeps_verified_and_qualifies_unsupported(self):
        """Verified claims stay in the answer; unsupported ones are demoted."""
        context = [{
            "file": "a.py",
            "code": [
                {
                    "name": "process_commands",
                    "line": 10,
                    "source": (
                        "10: def process_commands(processors):\n"
                        "11:     stream = ()\n"
                        "12:     for p in processors:\n"
                        "13:         stream = p(stream)"
                    ),
                },
                {
                    "name": "helper",
                    "line": 50,
                    "source": "50: def helper():\n51:     return 1",
                },
            ],
            "matches": [],
            "imports": [],
        }]

        answer = validate_citations(
            "process_commands builds a stream from the processors [a.py:12]. "
            "It also handles command dispatch errors via retry logic "
            "[bogus.py:99].",
            context,
        )

        # The verified claim is presented as the answer body.
        self.assertIn("process_commands builds a stream", answer)
        self.assertIn("[a.py:12]", answer)

        # The unverified claim is not asserted as fact; it is demoted.
        self.assertIn("not part of the answer", answer.lower())
        self.assertIn("handles command dispatch errors", answer)

        # A marker distinguishes the two sections.
        self.assertIn("not established by the retrieved source", answer.lower())
        self.assertIn("supported by the retrieved code", answer.lower())

    def test_all_unsupported_answer_says_no_confident_answer(self):
        """When nothing verifies, the response must not assert the claims."""
        context = [{
            "file": "a.py",
            "code": [{
                "name": "helper",
                "line": 5,
                "source": "5: def helper():\n6:     return 1",
            }],
            "matches": [],
            "imports": [],
        }]

        answer = validate_citations(
            "process_commands executes command definitions sequentially "
            "[a.py:5].",
            context,
        )

        lowered = answer.lower()
        self.assertIn("does not support a confident answer", lowered)
        # The unsupported claim is still shown, but labelled.
        self.assertIn("process_commands executes", answer)
        self.assertIn("not part of the answer", lowered)

    def test_unsupported_claim_not_presented_as_verified_answer(self):
        """The unsupported claim must not appear before the demotion marker."""
        context = [{
            "file": "a.py",
            "code": [{
                "name": "helper",
                "line": 5,
                "source": "5: def helper():\n6:     return 1",
            }],
            "matches": [],
            "imports": [],
        }]

        answer = validate_citations(
            "process_commands executes command definitions sequentially "
            "[a.py:5].",
            context,
        )

        # The confident assertion must live only inside the flagged section,
        # not in the leading answer body.
        body, _, flagged = answer.partition("not part of the answer")
        self.assertNotIn("process_commands executes", body.lower())
        self.assertIn("process_commands executes", flagged.lower())

    def test_uncited_claim_naming_absent_symbol_is_flagged(self):
        """An uncited claim naming symbols absent from all context is demoted."""
        context = [{
            "file": "a.py",
            "code": [{
                "name": "helper",
                "line": 5,
                "source": "5: def helper():\n6:     return 1",
            }],
            "matches": [],
            "imports": [],
        }]

        answer = validate_citations(
            "The routine then calls retry_transient_errors to recover.",
            context,
        )

        lowered = answer.lower()
        self.assertIn("not part of the answer", lowered)
        self.assertIn("retry_transient_errors", answer)

    def test_uncited_claim_with_symbol_present_in_context_is_left(self):
        """An uncited claim whose symbols are in context is not demoted."""
        context = [{
            "file": "a.py",
            "code": [{
                "name": "process_commands",
                "line": 5,
                "source": "5: def process_commands(processors):\n6:     return 1",
            }],
            "matches": [],
            "imports": [],
        }]

        answer = validate_citations(
            "The routine calls process_commands to recover.",
            context,
        )

        lowered = answer.lower()
        self.assertNotIn("not part of the answer", lowered)
        self.assertIn("process_commands", answer)


if __name__ == "__main__":
    unittest.main()

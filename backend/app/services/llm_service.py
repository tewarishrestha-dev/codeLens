import os
import re
import requests

# Ollama configuration. Override via environment for non-local deployments.
# Base URL is normalized so /api/generate is never double-slashed.
OLLAMA_BASE_URL = (
    os.environ.get("CODELENS_OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
)
OLLAMA_MODEL = os.environ.get("CODELENS_OLLAMA_MODEL", "qwen2.5-coder:3b")


def _ollama_generate_url():
    return f"{OLLAMA_BASE_URL}/api/generate"


CITATION_PATTERN = re.compile(r"\[([^]\n:]+):(\d+)\]")

# Content words that make a claim checkable against a cited source line.
# Function/method/class names (e.g. process_commands, run_subcommand) are the
# strongest signal that the claim is about this repository's code rather than
# generic prose.
_NAME_WORD_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{3,}")

# Generic vocabulary that must NOT be required to appear in a cited line;
# requiring these would flag nearly every legitimately grounded claim.
_GENERIC_WORDS = {
    "code", "codes", "function", "functions", "method", "methods",
    "class", "classes", "returns", "return", "value", "values",
    "line", "lines", "file", "files", "name", "names", "called",
    "calls", "call", "args", "argument", "arguments", "parameter",
    "parameters", "object", "objects", "data", "type", "types",
    "string", "strings", "list", "lists", "dict", "element", "elements",
    "variable", "variables", "argument", "defined", "defines", "definition",
    "body", "source", "context", "example", "examples", "default", "defaults",
    "result", "results", "input", "output", "state", "uses", "using", "used",
    "invokes", "invoked", "invoke", "runs", "run", "executes", "execute",
    "creates", "create", "adds", "add", "sets", "set", "gets", "get",
    "checks", "check", "handles", "handle", "processes", "process",
    "iterates", "iterate", "applies", "apply", "provides", "provide",
    "contains", "contain", "includes", "include", "represents", "represent",
    "builds", "build", "reads", "writes", "raises", "retries", "retry",
    "dispatches", "dispatch", "completes", "fails", "follows", "loops",
    "streams", "iterates", "expects", "permits", "forbids", "accepts",
    "indicates", "indicate", "specifies", "specify", "denotes", "denote",
    "sequence", "sequential", "order", "first", "then", "when", "where",
    "which", "that", "this", "these", "those", "with", "from", "into",
    "through", "while", "during", "before", "after", "above", "below",
    "between", "under", "over", "within", "without", "against", "toward",
    "about", "than", "then", "thus", "hence", "because", "since", "while",
    "however", "therefore", "moreover", "furthermore", "nevertheless",
    "true", "false", "none", "null", "yes", "no", "not", "also", "only",
    "just", "even", "still", "already", "always", "never", "often",
    "sometimes", "usually", "likely", "possible", "available", "used",
    "based", "related", "corresponding", "respective", "given", "certain",
    "various", "multiple", "single", "each", "every", "any", "all",
    "some", "one", "two", "three", "many", "few", "several", "both",
    "either", "neither", "whether", "whose", "here", "there", "now",
    "then", "once", "again", "instead", "rather", "almost", "quite",
    "rather", "enough", "almost", "nearly", "just", "only", "even",
}


def _path_matches(cited, retrieved):
    """True when a cited path refers to a retrieved file.

    Accepts the full repo-relative path, a trailing-suffix path, or the bare
    basename, so ``click/core.py``, ``core.py``, and ``src/click/core.py`` all
    resolve to the same retrieved file. Case-insensitive on Windows paths.
    A citation that omits the file extension (``click/core``) is also matched
    against the extension-stripped retrieved path.
    """
    cited = cited.replace("\\", "/").lower().lstrip("./")
    retrieved = retrieved.replace("\\", "/").lower()

    if not cited:
        return False

    if cited == retrieved:
        return True

    if retrieved.endswith("/" + cited):
        return True

    if cited == retrieved.split("/")[-1]:
        return True

    # Extension-tolerant match: the model sometimes drops ``.py``.
    if "." not in cited.split("/")[-1]:
        stem = re.sub(r"\.[A-Za-z0-9]+$", "", retrieved)

        if cited == stem or stem.endswith("/" + cited):
            return True

    return False


def _line_in_entry(code, line_number):
    """True when ``line_number`` falls inside a code entry's numbered source."""
    for source_line in code["source"].splitlines():
        match = re.match(r"^\s*(\d+):", source_line)

        if match and int(match.group(1)) == line_number:
            return True

    return False


def _resolve_symbol_citation(context, symbol, line_number):
    """Resolve ``symbol:line`` to a retrieved entry that defines ``symbol``.

    Small models often write a citation as ``funcname:line`` or ``mod.func:line``
    instead of the real ``path/to/file.py:line``. When the cited symbol names a
    function/method/class that is present in the retrieved context, return its
    real ``(file, name, line)`` so the citation can be grounded; otherwise
    return ``None``. A bare basename citation (``core.py``) is not a symbol, so
    it is ignored here.
    """
    token = symbol.replace("\\", "/").split("/")[-1]

    # Real file citations end in a code extension; those are handled by the
    # positional path check, not here.
    if re.search(r"\.(py|pyi|js|ts|jsx|tsx|go|rs|java|c|cc|cpp|h|hpp)$", token):
        return None

    # ``mod.func`` -> use the trailing attribute as the symbol.
    bare = token.split(".")[-1].strip()

    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", bare):
        return None

    for item in context:
        for code in item["code"]:
            if code["name"] != bare:
                continue

            if _line_in_entry(code, line_number):
                return item["file"], code["name"], code["line"]

    return None


def _entry_for_citation(context, file_path, line_number):
    """Return the (name, source) of the code entry containing a cited line.

    Falls back to ``None`` when the cited line is not inside any retrieved
    entry, so callers can skip lines they cannot verify against.
    """
    for item in context:
        if not _path_matches(file_path, item["file"]):
            continue

        for code in item["code"]:
            for source_line in code["source"].splitlines():
                match = re.match(r"^\s*(\d+):", source_line)

                if match and int(match.group(1)) == line_number:
                    plain = "\n".join(
                        re.sub(r"^\s*\d+:\s?", "", line)
                        for line in code["source"].splitlines()
                    )
                    return code["name"], plain

    return None


def _claim_is_supported(claim, entry_source):
    """Check that a claim's distinctive identifiers appear in its cited entry.

    A claim is flagged when it names repository identifiers (words containing
    an underscore, or long code-like names) that do NOT appear anywhere in the
    source of the entry the citation points into. Generic prose vocabulary is
    ignored so this only catches claims that invent repository-specific
    behavior about a different function than the one cited. Returns None when
    the claim has no checkable identifier words (nothing to verify against).
    """
    lowered_source = entry_source.lower()
    # Citation spans (e.g. [calculator.py:1]) are not claims about the
    # source; strip them so path fragments are not treated as identifiers
    # that must appear in the cited entry.
    prose = CITATION_PATTERN.sub("", claim)
    words = [
        word.lower()
        for word in _NAME_WORD_RE.findall(prose)
        if word.lower() not in _GENERIC_WORDS
        and (
            "_" in word
            or (word.islower() and len(word) >= 6)
            or (word[0].isupper() and len(word) >= 3)
        )
    ]

    if not words:
        return None

    missing = [word for word in words if word not in lowered_source]

    if not missing:
        return True

    return False


def _split_claims(answer):
    """Split an answer into claim units (sentences / bullet fragments).

    Sentence boundaries require the punctuation to follow a letter, digit, or
    closing bracket so that the ``:`` inside a ``[file:line]`` citation is never
    treated as a sentence end.
    """
    parts = re.split(
        r"(?<=[A-Za-z0-9)\]])[.!?]\s+|\n+",
        answer,
    )
    return [part.strip() for part in parts if part.strip()]


def _rewrite_citations(answer, context, unverified):
    """Resolve each ``[path:line]`` citation against the retrieved context.

    Positional matches are kept verbatim. ``symbol:line`` citations that name a
    real retrieved definition are rewritten to the real file path. Anything
    else is recorded in ``unverified`` and replaced with an explicit
    ``[unverified]`` marker so downstream formatting can qualify the claim.
    """
    def check(match):
        cited_path = match.group(1).replace("\\", "/")
        line_number = int(match.group(2))

        for item in context:
            file_path = item["file"].replace("\\", "/")

            for code in item["code"]:
                for source_line in code["source"].splitlines():
                    line_match = re.match(r"^\s*(\d+):", source_line)

                    if (
                        line_match
                        and int(line_match.group(1)) == line_number
                        and _path_matches(cited_path, file_path)
                    ):
                        return match.group(0)

        resolved = _resolve_symbol_citation(context, cited_path, line_number)

        if resolved is not None:
            real_file, _name, _line = resolved
            return f"[{real_file}:{line_number}]"

        label = f"{match.group(1)}:{line_number}"

        if label not in unverified:
            unverified.append(label)

        return f"[{label}] (unverified)"

    return CITATION_PATTERN.sub(check, answer)


def _uncited_symbol_words(claim):
    """Distinctive code-shaped identifiers in a claim that carries no citation.

    Only words that cannot be ordinary English prose are considered: names
    containing an underscore (``process_commands``) or camelCase/mixed case
    (``makeContext``). Plain lowercase words are ignored here because they are
    indistinguishable from prose vocabulary.
    """
    words = []

    for word in _NAME_WORD_RE.findall(claim):
        lowered = word.lower()

        if lowered in _GENERIC_WORDS:
            continue

        if "_" in word or re.search(r"[a-z][A-Z]", word):
            words.append(lowered)

    return words


def _check_claim_support(claim, context):
    """Heuristic support check for a single claim against the context.

    Returns ``True`` (supported), ``False`` (unsupported), or ``None`` (not
    checkable -- the claim carries no citation or no distinctive identifiers).
    This is a lexical heuristic, NOT full semantic verification: identifier
    presence is evidence the claim is about the right code, not proof that the
    claim is true. In particular, a claim that invents a call pattern using
    ordinary lowercase names that happen to exist elsewhere in the corpus cannot
    be caught lexically.
    """
    citations = list(CITATION_PATTERN.finditer(claim))

    # A claim carrying an unresolved-citation marker has, by construction, at
    # least one citation that failed to resolve against the retrieved source.
    if "(unverified)" in claim:
        return False

    if not citations:
        # An uncited claim that names code-shaped symbols absent from every
        # retrieved entry asserts behavior the evidence does not contain.
        corpus = "\n".join(
            code["source"].lower()
            for item in context
            for code in item["code"]
        )
        missing = [
            word
            for word in _uncited_symbol_words(claim)
            if word not in corpus
        ]

        if missing:
            return False

        return None

    saw_checkable = False
    missing = False

    for citation in citations:
        if citation.group(1) == "unverified":
            return False

        file_path = citation.group(1).replace("\\", "/")
        line_number = int(citation.group(2))
        entry = _entry_for_citation(context, file_path, line_number)

        if entry is None:
            continue

        _name, entry_source = entry
        result = _claim_is_supported(claim, entry_source)

        # The citation resolved to a real retrieved entry, so the claim made
        # a checkable assertion about it. Failing that check is unsupported.
        saw_checkable = True

        if result is False:
            missing = True

    if missing:
        return False

    if saw_checkable:
        return True

    return None


def _format_answer(verified, flagged):
    """Build the final answer, qualifying unsupported claims in place.

    Verified claims are presented as the answer. Claims that relied on an
    unverified citation or failed the support heuristic are demoted into a
    clearly-labelled review section instead of being asserted as fact. When
    nothing verified remains, the response says so explicitly rather than
    presenting guesses as an answer.
    """
    if verified:
        answer = "\n\n".join(verified)
    else:
        answer = (
            "The retrieved evidence does not support a confident answer "
            "to this question."
        )

    if flagged:
        answer += (
            "\n\nThe following statements were not established by the "
            "retrieved source and are not part of the answer:\n"
            + "\n".join(f"- {claim}" for claim in flagged)
        )

    if verified and flagged:
        answer += (
            "\n\nOnly the statements above marked as established are "
            "supported by the retrieved code. The remaining statements "
            "are unverified hypotheses, not verified findings."
        )

    return answer


def validate_citations(answer, context):
    """Split an answer into verified claims and unsupported ones.

    Citations are first resolved against the retrieved context (positional
    match or symbol rewrite). Each claim is then checked heuristically:
    a claim is verified only when every citation it carries resolved AND its
    distinctive identifiers appear in the cited entry. Unsupported claims are
    moved out of the answer body into a clearly-labelled section. This is a
    lexical heuristic, not full semantic verification -- identifier presence
    is treated as necessary evidence, never as proof.
    """
    unverified = []
    rewritten = _rewrite_citations(answer, context, unverified)

    verified = []
    flagged = []

    for claim in _split_claims(rewritten):
        claim = claim.strip()

        if not claim:
            continue

        support = _check_claim_support(claim, context)

        if support is False:
            flagged.append(claim)
        else:
            verified.append(claim)

    return _format_answer(verified, flagged)


def build_prompt(question, context):
    code_context = []

    for item in context:
        code_context.append(f"File: {item['file']}")

        for code in item["code"]:
            code_context.append(
                f"Function: {code['name']}\n"
                f"Line: {code['line']}\n"
                f"Source:\n{code['source']}"
            )

    return f"""You are CodeLens, a precise codebase analyst.

Answer using only the supplied code context.

Grounding rules:
- Answer strictly from the Source blocks below. Do not rely on prior knowledge of the library or framework.
- If the context does not contain the evidence needed to answer, say so explicitly instead of guessing.
- If the body of a function or method named in the question is not included below, state that the provided context does not contain it and do not describe what it does.
- Never invent function calls, variables, or code behavior.
- Do not assume one method calls another unless the source explicitly shows it.
- Distinguish facts from assumptions.

Citation rules:
- Support factual claims with citations in this format: [file_path:line].
- The file_path MUST be copied verbatim from a "File:" header above (or a suffix of it). Do not invent a filename, module name, or shorten it to a bare module like [click.py] or [main.py]. If the header says "File: src/click/core.py", cite [src/click/core.py:1234].
- Cite only line numbers that appear inside the Source block you are quoting from.
- Never cite a nearby line just because it belongs to the same function.
- For a calculation, cite the line containing the expression used.
- If exact line information is unavailable, say the line is unknown instead of inventing a line number.
- When you name a function, method, class, or variable in a claim, that exact identifier must appear on the line you cite for it. If you cannot find a cited line that contains the identifier, do not make the claim.

Command-execution disambiguation:
- Distinguish (a) shell/OS command execution (e.g. subprocess, os.system, os.popen), (b) framework command dispatch (the code that parses or invokes framework commands), and (c) functions whose names merely contain the word "command".
- A function whose name contains "command" is not automatically a command executor. Describe what the cited source actually does before naming it.
- If the supplied context does not show shell/OS execution, say so instead of presenting framework dispatch or a similarly-named helper as shell execution.

Code context:
{"\n\n".join(code_context)}

Question:
{question}

Answer in 2-4 sentences. Cite each key claim using [file_path:line]. For calculations, show the expression, result, and supporting citation. Avoid unnecessary numbered steps.
"""


def ask_llm(question, context):
    if not context:
        return "I could not find relevant code for this question."

    prompt = build_prompt(question, context)

    response = requests.post(
        _ollama_generate_url(),
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False
        },
        timeout=120
    )

    response.raise_for_status()

    answer = response.json()["response"]
    return validate_citations(answer, context)


def summarize_project(project_context):
    prompt = f"""You are CodeLens, an AI codebase analyst.

Analyze the project ONLY from the information provided below.

Rules:
- Do not invent line numbers or code details that are not provided.
- Use the source code to determine what functions actually do.
- Do not guess or invent functionality.
- If the information is insufficient, explicitly say so.
- Do not assume that a function named "train" means machine learning.
- Entry points are identified by CodeLens using filename-based heuristics.
- Do not claim that an entry point is definitely executed at runtime.
- When describing imports, use the exact import information provided.
- Do not invent or reconstruct import statements.
- Base every statement on the supplied information.

Project name:
{project_context["project_name"]}

Files:
{project_context["files"]}

Entry points:
{project_context["entry_points"]}

Functions:
{project_context["functions"]}

Classes:
{project_context["classes"]}

Dependencies:
{project_context["dependencies"]}

Imports:
{project_context["imports"]}

Directories:
{project_context["directories"]}

Source code:
{project_context["source_code"]}

Give a concise analysis with exactly these sections:

1. Project overview
2. Structure
3. Entry points
4. Main components
5. Dependency flow
6. What cannot be determined
"""

    response = requests.post(
        _ollama_generate_url(),
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False
        },
        timeout=120
    )

    response.raise_for_status()

    return response.json()["response"]
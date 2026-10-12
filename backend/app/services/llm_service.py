import re
import requests


CITATION_PATTERN = re.compile(r"\[([^]\n:]+):(\d+)\]")


def validate_citations(answer, context):
    """Mark citations that are not backed by the retrieved source.

    This is an allow-list (positional) check: it confirms that the cited file
    and line were actually retrieved. It does NOT check that the cited line
    supports the claim, so it is not semantic validation.
    """
    valid_lines = set()

    for item in context:
        file_path = item["file"].replace("\\", "/")
        file_names = {file_path, file_path.split("/")[-1]}

        for code in item["code"]:
            for line in code["source"].splitlines():
                match = re.match(r"^\s*(\d+):", line)

                if match:
                    for name in file_names:
                        valid_lines.add((name, int(match.group(1))))

    unverified = []

    def check(match):
        file_path = match.group(1).replace("\\", "/")
        line_number = int(match.group(2))

        if (file_path, line_number) in valid_lines:
            return match.group(0)

        if (file_path.split("/")[-1], line_number) in valid_lines:
            return match.group(0)

        citation = f"{match.group(1)}:{line_number}"

        if citation not in unverified:
            unverified.append(citation)

        return f"[{citation} (unverified: line not in retrieved source)]"

    answer = CITATION_PATTERN.sub(check, answer)
    answer = re.sub(r"\s*\*\*\d+\*\*\s*$", "", answer).strip()

    if unverified:
        answer += (
            "\n\nNote: these citations were not found in the retrieved "
            "source, so the claims they support are unverified: "
            + ", ".join(unverified) + "."
        )

    return answer


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
- Cite only line numbers that contain the exact code supporting your claim.
- Never cite a nearby line just because it belongs to the same function.
- For a calculation, cite the line containing the expression used.
- If exact line information is unavailable, say the line is unknown instead of inventing a line number.

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
        "http://127.0.0.1:11434/api/generate",
        json={
            "model": "qwen2.5-coder:3b",
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
        "http://127.0.0.1:11434/api/generate",
        json={
            "model": "qwen2.5-coder:3b",
            "prompt": prompt,
            "stream": False
        },
        timeout=120
    )

    response.raise_for_status()

    return response.json()["response"]
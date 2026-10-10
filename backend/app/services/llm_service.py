import requests


def ask_llm(question, context):
    if not context:
        return "I could not find relevant code for this question."

    code_context = []

    for item in context:
        code_context.append(f"File: {item['file']}")

        for code in item["code"]:
            code_context.append(
                f"Function: {code['name']}\n"
                f"Line: {code['line']}\n"
                f"Source:\n{code['source']}"
            )

    prompt = f"""You are CodeLens, a precise codebase analyst.

Answer using only the supplied code context.

Rules:
- Never invent function calls, method calls, variables, or code behavior.
- Do not assume one method calls another unless the source explicitly shows that call.
- For numerical questions, trace the actual expressions and calculate the result step by step.
- Distinguish facts from assumptions.
- If the required source is missing, say so.
- Explain the actual code, not what similar code might normally do.

Code context:
{"\n\n".join(code_context)}

Question:
{question}

Give a concise, accurate answer. For calculations, show the relevant expression and final result.
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
import ast
from pathlib import Path

def parse_python_file(file_path: Path):
    try:
        source = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return {
            "imports": [],
            "functions": [],
            "classes": []
        }

    tree = ast.parse(source)

    imports = []
    functions = []
    classes = []
    calls = []

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    if isinstance(child.func, ast.Name):
                        calls.append({
                            "function": node.name,
                            "calls": child.func.id
                        })
                    elif isinstance(child.func, ast.Attribute):
                        calls.append({
                            "function": node.name,
                            "calls": child.func.attr
                        })

    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append({
                "name": node.name,
                "line": node.lineno,
                "arguments": [arg.arg for arg in node.args.args]
            })

        elif isinstance(node, ast.ClassDef):
            methods = []

            for method in node.body:
                if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    methods.append({
                        "name": method.name,
                        "line": method.lineno,
                        "arguments": [arg.arg for arg in method.args.args]
                    })

            classes.append({
                "name": node.name,
                "line": node.lineno,
                "methods": methods
            })

    return {
        "imports": imports,
        "functions": functions,
        "classes": classes,
        "calls": calls,
    }
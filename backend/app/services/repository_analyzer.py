from pathlib import Path

from .repository_scanner import scan_repository
from .repository_parser import parse_repository
from .dependency_analyzer import build_dependencies
from .call_analyzer import build_call_graph
from .architecture_analyzer import build_architecture_summary

ENTRY_POINTS = {
    "main.py",
    "app.py",
    "server.py",
    "manage.py",
    "__init__.py",
    "cli.py",
    "core.py",
    "wsgi.py",
    "asgi.py",
    "index.js",
    "index.ts",
    "index.jsx",
    "index.tsx",
    "main.js",
    "main.ts",
    "main.jsx",
    "main.tsx",
    "server.js",
    "server.ts",
    "app.js",
    "app.ts",
    "App.jsx",
    "App.tsx",
}


def analyze_repository(repo_path: Path):
    code_analysis = parse_repository(repo_path)

    entry_points = [
        path
        for path in code_analysis
        if Path(path).name in ENTRY_POINTS
    ]

    # Fallback: if no entry points found, look for top-level package __init__.py
    # files (paths with 2-3 segments like pkg/__init__.py or src/pkg/__init__.py)
    if not entry_points:
        for path in code_analysis:
            p = Path(path)
            parts = p.parts
            if p.name == "__init__.py" and len(parts) <= 3:
                entry_points.append(path)

    dependencies = build_dependencies(code_analysis)
    call_graph = build_call_graph(code_analysis)

    architecture = build_architecture_summary(
        code_analysis,
        dependencies,
        entry_points,
    )

    return {
        "tree": scan_repository(repo_path),
        "code_analysis": code_analysis,
        "dependencies": dependencies,
        "call_graph": call_graph,
        "entry_points": entry_points,
        "architecture": architecture,
    }
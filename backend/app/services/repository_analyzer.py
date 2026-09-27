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
}


def analyze_repository(repo_path: Path):
    code_analysis = parse_repository(repo_path)

    entry_points = [
        path
        for path in code_analysis
        if Path(path).name in ENTRY_POINTS
    ]

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
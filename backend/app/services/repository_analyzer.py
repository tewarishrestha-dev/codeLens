from pathlib import Path

from .repository_scanner import scan_repository
from .repository_parser import parse_repository
from .dependency_analyzer import build_dependencies
from .call_analyzer import build_call_graph


def analyze_repository(repo_path: Path):
    code_analysis = parse_repository(repo_path)

    return {
        "tree": scan_repository(repo_path),
        "code_analysis": code_analysis,
        "dependencies": build_dependencies(code_analysis),
        "call_graph": build_call_graph(code_analysis)
    }
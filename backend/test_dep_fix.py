"""Inline test: verify build_dependencies resolves intra-package Python imports."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.services.dependency_analyzer import build_dependencies

# Mock Click-like package structure
code_analysis = {
    "src/click/__init__.py": {
        "imports": ["core", "exceptions", "types", "utils"],
        "functions": [], "classes": [], "calls": [],
    },
    "src/click/core.py": {
        "imports": ["exceptions", "formatting", "utils", "types"],
        "functions": [], "classes": [], "calls": [],
    },
    "src/click/exceptions.py": {
        "imports": ["utils"],
        "functions": [], "classes": [], "calls": [],
    },
    "src/click/utils.py": {
        "imports": [],
        "functions": [], "classes": [], "calls": [],
    },
    "src/click/types.py": {
        "imports": ["exceptions"],
        "functions": [], "classes": [], "calls": [],
    },
}

result = build_dependencies(code_analysis)
forward = result["forward"]

total_edges = sum(len(deps) for deps in forward.values())
print(f"Total dependency edges: {total_edges}")

# Print details
for src, deps in forward.items():
    if deps:
        print(f"  {src} -> {deps}")

assert total_edges > 0, "FAIL: expected dependency edges > 0"
print("PASS")

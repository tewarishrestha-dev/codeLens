from pathlib import Path
import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from backend.app.models.github import GitHubRequest
from backend.app.models.repository import Repository
from backend.app.services.github_service import clone_repository
from backend.app.services.repository_scanner import scan_repository
from backend.app.services.zip_service import extract_zip
from backend.app.services.file_reader import read_file
from backend.app.services.repository_store import save_repository
from backend.app.services.repository_store import get_repository
from backend.app.services.repository_store import list_repositories
from backend.app.services.repository_store import delete_repository
from backend.app.services.repository_store import RepositoryFilesMissing
from backend.app.services.repository_store import data_dir
from backend.app.services.repository_analyzer import analyze_repository
from backend.app.services.call_analyzer import build_execution_flow
from backend.app.services.code_search import search_code
from backend.app.services.context_builder import (
    build_context,
    build_project_context
)
from backend.app.services.llm_service import ask_llm, summarize_project
import tempfile

# CORS: comma-separated list of allowed frontend origins.
# Unset -> local Vite dev server only. Wildcards are not used.
_DEFAULT_CORS_ORIGINS = "http://localhost:5173"


def _parse_cors_origins(raw: str) -> list[str]:
    """Split, trim, and drop empty entries from a comma-separated origin list."""
    origins = []
    for part in (raw or "").split(","):
        origin = part.strip()
        if origin:
            origins.append(origin)
    return origins or [_DEFAULT_CORS_ORIGINS]


CORS_ORIGINS = _parse_cors_origins(
    os.environ.get("CODELENS_CORS_ORIGINS", _DEFAULT_CORS_ORIGINS)
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def load_repository_or_404(repository_id: str):
    """Resolve a workspace, translating store errors to HTTP responses.

    - Unknown id -> 404
    - Known id whose files were deleted -> 410 Gone (never serve stale
      workspaces as if they were usable)
    """
    try:
        repository = get_repository(repository_id)
    except RepositoryFilesMissing:
        raise HTTPException(
            status_code=410,
            detail="Repository files are missing on disk. Remove this workspace and re-analyze the project.",
        )

    if repository is None:
        raise HTTPException(status_code=404, detail="Repository not found")

    return repository


@app.get("/")
def home():
    return {"message": "CodeLens API is running"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/analyze/github")
def analyze_github(request: GitHubRequest):
    repo_path, repo_name = clone_repository(request.url)

    analysis = analyze_repository(repo_path)
    analysis["tree"]["name"] = repo_name

    repository_id = save_repository(
        str(repo_path),
        repo_name,
        analysis["tree"],
        analysis["code_analysis"],
        analysis["dependencies"],
        analysis["call_graph"],
        analysis["entry_points"],
        analysis["architecture"]
    )

    return {
        "repository_id": repository_id,
        "name": repo_name,
        "tree": analysis["tree"],
        "code_analysis": analysis["code_analysis"],
        "dependencies": analysis["dependencies"],
        "call_graph": analysis["call_graph"],
        "entry_points": analysis["entry_points"],
        "architecture": analysis["architecture"],
        "directories": analysis["architecture"]["directories"],
        
    }

@app.post("/analyze/zip")
def analyze_zip(file: UploadFile = File(...)):
    repo_name = Path(file.filename).stem
    temp_dir = data_dir()
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_file = temp_dir / f"{repo_name}.zip"

    temp_file.write_bytes(file.file.read())

    repo_path = extract_zip(temp_file)
    temp_file.unlink()

    analysis = analyze_repository(repo_path)
    analysis["tree"]["name"] = repo_name

    repository_id = save_repository(
        str(repo_path),
        repo_name,
        analysis["tree"],
        analysis["code_analysis"],
        analysis["dependencies"],
        analysis["call_graph"],
        analysis["entry_points"],
        analysis["architecture"]
    )

    return {
        "repository_id": repository_id,
        "name": repo_name,
        "tree": analysis["tree"],
        "code_analysis": analysis["code_analysis"],
        "dependencies": analysis["dependencies"],
        "call_graph": analysis["call_graph"],
        "entry_points": analysis["entry_points"],
        "architecture": analysis["architecture"],
        "directories": analysis["architecture"]["directories"],
    }

@app.get("/file")
def get_file(repository_id: str, file_path: str):

    repository = load_repository_or_404(repository_id)

    try:
        content = read_file(
            Path(repository["path"]),
            file_path
        )

        return {"content": content}

    except ValueError as e:
        raise HTTPException(
            status_code=403,
            detail=str(e)
        )

    except Exception as e:
        print("FILE ERROR:", repr(e))
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@app.get("/repositories")
def get_repositories():
    return {"repositories": list_repositories()}


@app.delete("/repository/{repository_id}")
def remove_repository(repository_id: str):
    removed = delete_repository(repository_id)

    if not removed:
        raise HTTPException(status_code=404, detail="Repository not found")

    return {"repository_id": repository_id, "removed": True}


@app.get("/repository/{repository_id}")
def get_repository_info(repository_id: str):
    repository = load_repository_or_404(repository_id)

    return {
        "repository_id": repository_id,
        "name": repository["name"],
        "path": repository["path"],
        "tree": repository["tree"],
        "code_analysis": repository["code_analysis"],
        "dependencies": repository["dependencies"],
        "call_graph": repository["call_graph"],
        "entry_points": repository["entry_points"],
        "architecture": repository["architecture"],
    }


@app.get("/repository/{repository_id}/dependencies")
def get_dependencies(repository_id: str):
    repository = load_repository_or_404(repository_id)

    return {
        "repository_id": repository_id,
        "dependencies": repository["dependencies"]
    }


@app.get("/repository/{repository_id}/call-graph")
def get_call_graph(repository_id: str):
    repository = load_repository_or_404(repository_id)

    return {
        "repository_id": repository_id,
        "call_graph": repository["call_graph"]
    }


@app.get("/repository/{repository_id}/flow")
def get_execution_flow(repository_id: str, entry_point: str):
    repository = load_repository_or_404(repository_id)

    flow = build_execution_flow(
        repository["call_graph"],
        entry_point
    )

    return {
        "entry_point": entry_point,
        "steps": flow
    }


@app.get("/repository/{repository_id}/search")
def search_repository(
    repository_id: str,
    query: str
):
    repository = load_repository_or_404(repository_id)

    if not query.strip():
        return {"results": []}

    results = search_code(
        repository["code_analysis"],
        query
    )

    return {
        "query": query,
        "results": results
    }

@app.get("/repository/{repository_id}/context")
def get_context(
    repository_id: str,
    query: str
):
    repository = load_repository_or_404(repository_id)

    if not query.strip():
        return {"context": []}
    
    print("FILES ANALYZED:", len(repository["code_analysis"]))
    print("RUN_COMMAND MATCHES:", [
        (path, f["name"], f["line"])
        for path, data in repository["code_analysis"].items()
        for f in data.get("functions", [])
        if "run_command" in f["name"].lower()
    ])

    search_results = search_code(
        repository["code_analysis"],
        query,
        repository["path"]
    )

    context = build_context(
    repository["path"],
    repository["code_analysis"],
    search_results,
    repository["call_graph"]
    )
    return {
        "query": query,
        "context": context
    }

@app.get("/repository/{repository_id}/ask")
def ask_codebase(
    repository_id: str,
    question: str
):
    repository = load_repository_or_404(repository_id)

    if not question.strip():
        return {"answer": ""}

    search_results = search_code(
        repository["code_analysis"],
        question,
        repository["path"]
    )

    context = build_context(
    repository["path"],
    repository["code_analysis"],
    search_results,
    repository["call_graph"]
    )

    answer = ask_llm(
        question,
        context
    )

    return {
        "question": question,
        "answer": answer,
        "context": context
    }

@app.get("/repository/{repository_id}/summary")
def summarize_codebase(repository_id: str):
    repository = load_repository_or_404(repository_id)

    project_context = build_project_context(repository)

    summary = summarize_project(project_context)

    return {
        "summary": summary
    }
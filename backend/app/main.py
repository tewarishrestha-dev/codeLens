from pathlib import Path
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
from backend.app.services.repository_analyzer import analyze_repository
from backend.app.services.call_analyzer import build_execution_flow
import tempfile

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
        analysis["call_graph"]
    )

    return {
        "repository_id": repository_id,
        "name": repo_name,
        "tree": analysis["tree"],
        "code_analysis": analysis["code_analysis"],
        "dependencies": analysis["dependencies"],
        "call_graph": analysis["call_graph"]
    }

@app.post("/analyze/zip")
def analyze_zip(file: UploadFile = File(...)):
    repo_name = Path(file.filename).stem
    temp_file = Path("E:/CodeLensData") / f"{repo_name}.zip"

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
        analysis["entry_points"]
    )

    return {
        "repository_id": repository_id,
        "name": repo_name,
        "tree": analysis["tree"],
        "code_analysis": analysis["code_analysis"],
        "dependencies": analysis["dependencies"],
        "call_graph": analysis["call_graph"],
        "entry_points": analysis["entry_points"]
    }

@app.get("/file")
def get_file(repository_id: str, file_path: str):

    repository = get_repository(repository_id)

    if repository is None:
        raise HTTPException(status_code=404, detail="Repository not found")

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

@app.get("/repository/{repository_id}")
def get_repository_info(repository_id: str):
    repository = get_repository(repository_id)

    if repository is None:
        raise HTTPException(status_code=404, detail="Repository not found")

    return {
        "repository_id": repository_id,
        "name": repository["name"],
        "tree": repository["tree"],
        "code_analysis": repository["code_analysis"],
        "dependencies": repository["dependencies"],
        "call_graph": repository["call_graph"]
    }

@app.get("/repository/{repository_id}/dependencies")
def get_dependencies(repository_id: str):
    repository = get_repository(repository_id)

    if repository is None:
        raise HTTPException(status_code=404, detail="Repository not found")

    return {
        "repository_id": repository_id,
        "dependencies": repository["dependencies"]
    }

@app.get("/repository/{repository_id}/call-graph")
def get_call_graph(repository_id: str):
    repository = get_repository(repository_id)

    if repository is None:
        raise HTTPException(status_code=404, detail="Repository not found")

    return {
        "repository_id": repository_id,
        "call_graph": repository["call_graph"]
    }

@app.get("/repository/{repository_id}/flow")
def get_execution_flow(repository_id: str, entry_point: str):
    repository = get_repository(repository_id)

    if repository is None:
        raise HTTPException(
            status_code=404,
            detail="Repository not found"
        )

    flow = build_execution_flow(
        repository["call_graph"],
        entry_point
    )

    return {
    "entry_point": entry_point,
    "steps": flow
}
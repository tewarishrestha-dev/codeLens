import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Metadata index location. Overridable for tests; matches the storage
# location already used by the github/zip ingestion services.
DATA_DIR_ENV = "CODELENS_DATA_DIR"
DEFAULT_DATA_DIR = "E:/CodeLensData"

# In-memory cache: repository_id -> full analysis dict. Analysis objects are
# intentionally NOT persisted; they are rebuilt from the stored repository
# files on first access after a restart (see get_repository).
repositories = {}

_index = None
_lock = threading.RLock()


class RepositoryFilesMissing(Exception):
    """The workspace is known to the index but its files no longer exist."""


def data_dir() -> Path:
    return Path(os.environ.get(DATA_DIR_ENV) or DEFAULT_DATA_DIR)


def _index_path() -> Path:
    return data_dir() / "repositories.json"


def _load_index():
    # Callers hold _lock.
    global _index
    if _index is not None:
        return _index

    path = _index_path()

    try:
        if path.exists():
            _index = json.loads(path.read_text(encoding="utf-8"))
        else:
            _index = {}
    except (OSError, json.JSONDecodeError):
        _index = {}

    return _index


def _write_index():
    # Callers hold _lock. Atomic replace so a crash mid-write cannot
    # corrupt the index.
    path = _index_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(_load_index(), indent=2), encoding="utf-8")
    os.replace(tmp, path)


def _now():
    return datetime.now(timezone.utc).isoformat()


def reset_store():
    """Clear in-memory state and re-read the index from disk (used by tests)."""
    global _index
    with _lock:
        repositories.clear()
        _index = None


def save_repository(
    repo_path,
    repo_name,
    tree,
    code_analysis,
    dependencies,
    call_graph,
    entry_points,
    architecture
):
    repository_id = str(uuid.uuid4())

    with _lock:
        index = _load_index()

        # Reuse the id when this location is already known so workspace ids
        # stay stable across re-analysis and backend restarts.
        for existing_id, meta in index.items():
            if meta.get("path") == str(repo_path):
                repository_id = existing_id
                break

        existing_meta = index.get(repository_id, {})

        index[repository_id] = {
            "repository_id": repository_id,
            "name": repo_name,
            "path": str(repo_path),
            "created_at": existing_meta.get("created_at", _now()),
            "last_opened_at": _now(),
        }
        _write_index()

        repositories[repository_id] = {
            "path": repo_path,
            "name": repo_name,
            "tree": tree,
            "code_analysis": code_analysis,
            "dependencies": dependencies,
            "call_graph": call_graph,
            "entry_points": entry_points,
            "architecture": architecture,
        }

    return repository_id


def get_repository(repository_id):
    """Return the full analysis for a workspace, rebuilding it from the
    stored repository files when it is not cached in memory.

    Returns None for unknown ids. Raises RepositoryFilesMissing when the
    workspace is known but its directory has been deleted.
    """
    with _lock:
        cached = repositories.get(repository_id)

        if cached is not None:
            if Path(cached["path"]).exists():
                return cached

            raise RepositoryFilesMissing(repository_id)

        meta = _load_index().get(repository_id)

        if meta is None:
            return None

        repo_path = Path(meta["path"])

        if not repo_path.exists():
            raise RepositoryFilesMissing(repository_id)

        # Deferred import: keeps this module dependency-light and avoids
        # any import cycle with the analyzer package.
        from .repository_analyzer import analyze_repository

        analysis = analyze_repository(repo_path)
        analysis["tree"]["name"] = meta["name"]

        meta["last_opened_at"] = _now()
        _write_index()

        repositories[repository_id] = {
            "path": meta["path"],
            "name": meta["name"],
            "tree": analysis["tree"],
            "code_analysis": analysis["code_analysis"],
            "dependencies": analysis["dependencies"],
            "call_graph": analysis["call_graph"],
            "entry_points": analysis["entry_points"],
            "architecture": analysis["architecture"],
        }

        return repositories[repository_id]


def list_repositories():
    """Return workspace metadata (most recently opened first).

    Entries whose directory no longer exists are included with
    available=False so the UI can flag them instead of pretending they
    are usable.
    """
    with _lock:
        entries = []

        for meta in _load_index().values():
            entries.append({
                "repository_id": meta["repository_id"],
                "name": meta["name"],
                "path": meta["path"],
                "created_at": meta.get("created_at"),
                "last_opened_at": meta.get("last_opened_at"),
                "available": Path(meta["path"]).exists(),
            })

        entries.sort(key=lambda e: e.get("last_opened_at") or "", reverse=True)

        return entries


def delete_repository(repository_id):
    """Remove a workspace from the index and memory.

    Files on disk are deliberately left untouched: ingestion paths may
    point at user-owned directories, and removal from CodeLens should
    never delete source code. Returns True when something was removed.
    """
    with _lock:
        index = _load_index()
        known = repository_id in index or repository_id in repositories

        index.pop(repository_id, None)
        repositories.pop(repository_id, None)

        if known:
            _write_index()

        return known

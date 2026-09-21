import uuid


repositories = {}

def save_repository(
    repo_path,
    repo_name,
    tree,
    code_analysis,
    dependencies,
    call_graph,
    entry_points
):
    repository_id = str(uuid.uuid4())

    repositories[repository_id] = {
        "path": repo_path,
        "name": repo_name,
        "tree": tree,
        "code_analysis": code_analysis,
        "dependencies": dependencies,
        "call_graph": call_graph,
        "entry_points": entry_points,
    }

    return repository_id


def get_repository(repository_id):
    return repositories.get(repository_id)
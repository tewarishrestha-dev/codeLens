from pydantic import BaseModel


class GitHubRequest(BaseModel):
    url: str
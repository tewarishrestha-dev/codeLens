from pydantic import BaseModel


class Repository(BaseModel):
    name: str
    path: str
    tree: dict
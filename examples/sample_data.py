"""
Shared sample data, entities, models, and repository for examples.
"""

from uuid import UUID

from pydantic import BaseModel

from src.entities import BaseEntity
from src.repository import Repository


# Canonical Post entity
class Post(BaseEntity):
    title: str = "Untitled Post"
    content: str = "No content provided"


# Canonical Post search model
class PostSearch(BaseModel):
    id: UUID | None = None
    title: str | None = None
    content: str | None = None


# Canonical Post update model
class PostUpdate(BaseModel):
    title: str | None = None
    content: str | None = None


# Canonical Post repository
class PostRepository(Repository[Post, PostSearch, PostUpdate]):
    def __init__(self):
        super().__init__(Post, PostSearch, PostUpdate, "posts")

from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.entities import BaseEntity, SortOrder


class Post(BaseEntity):
    title: str
    content: str
    # Optional/extended fields used by some tests
    published: bool = False
    category: str | None = None
    author_id: UUID | None = None


# Search models - all fields optional for flexible querying
class PostSearch(BaseModel):
    id: UUID | None = None
    title: str | None = None
    content: str | None = None
    published: bool | None = None
    category: str | None = None
    author_id: UUID | None = None


# Update model - defines which fields can be updated
class PostUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    published: bool | None = None
    category: str | None = None
    author_id: UUID | None = None


class PostSort(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    """Defines which fields can be sorted for Post entity"""
    title: SortOrder | None = None
    content: SortOrder | None = None
    id: SortOrder | None = None
    category: SortOrder | None = None

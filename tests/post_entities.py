from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.entities import BaseEntity, SortOrder


class Post(BaseEntity):
    title: str
    content: str

# Search models - all fields optional for flexible querying
class PostSearch(BaseModel):
    id: Optional[UUID] = None
    title: Optional[str] = None
    content: Optional[str] = None

# Update model - defines which fields can be updated
class PostUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None

class PostSort(BaseModel):

    model_config = ConfigDict(use_enum_values=True)
    """Defines which fields can be sorted for Post entity"""
    title: Optional[SortOrder] = None
    content: Optional[SortOrder] = None
    id: Optional[SortOrder] = None

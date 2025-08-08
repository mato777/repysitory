from pydantic import BaseModel
from uuid import UUID, uuid4
from typing import Optional, List
from enum import Enum

class Entity(BaseModel):
    id: UUID = uuid4()

class Post(Entity):
    title: str
    content: str

# Search models - all fields optional for flexible querying
class PostSearch(BaseModel):
    id: Optional[UUID] = None
    title: Optional[str] = None
    content: Optional[str] = None

# Sorting functionality
class SortOrder(str, Enum):
    ASC = "ASC"
    DESC = "DESC"

class SortField(BaseModel):
    field: str
    order: SortOrder = SortOrder.ASC

class PostSort(BaseModel):
    """Defines which fields can be sorted for Post entity"""
    title: Optional[SortOrder] = None
    content: Optional[SortOrder] = None
    id: Optional[SortOrder] = None

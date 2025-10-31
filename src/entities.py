from enum import Enum
from typing import ClassVar
from uuid import UUID, uuid4

from pydantic import BaseModel
from pydantic.config import ConfigDict


class Field[T]:
    """Type-safe field definition for schema classes.

    Usage:
        class PostSchema(SchemaBase):
            published = Field[bool]("published")
            title = Field[str]("title")

    This allows for:
        repo.where(PostSchema.published, True)
        repo.where_in(PostSchema.title, ["Title 1", "Title 2"])
    """

    def __init__(self, column_name: str):
        """
        Args:
            column_name: The actual database column name
        """
        self._column_name = column_name

    @property
    def column(self) -> str:
        """Return the underlying database column name."""
        return self._column_name

    def __str__(self) -> str:
        """Return the column name when used in queries"""
        return self._column_name

    def __repr__(self) -> str:
        return f"Field({self._column_name})"


class SchemaBase:
    """Base class for schema definitions with type-safe fields.

    Usage:
        class PostSchema(SchemaBase):
            published = Field[bool]("published")
            title = Field[str]("title")
            created_at = Field[datetime]("created_at")
    """

    pass


class BaseEntity(BaseModel):
    """Base entity class for all database models."""

    model_config: ClassVar[ConfigDict] = ConfigDict(use_enum_values=True, extra="allow")
    id: UUID = uuid4()


# Sorting functionality
class SortOrder(str, Enum):
    ASC = "ASC"
    DESC = "DESC"

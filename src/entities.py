from enum import Enum
from typing import ClassVar
from uuid import UUID, uuid4

from pydantic import BaseModel
from pydantic.config import ConfigDict


class BaseEntity(BaseModel):
    """Base entity class for all database models."""

    model_config: ClassVar[ConfigDict] = ConfigDict(
        use_enum_values=True, extra="ignore"
    )
    id: UUID = uuid4()


# Sorting functionality
class SortOrder(str, Enum):
    ASC = "ASC"
    DESC = "DESC"

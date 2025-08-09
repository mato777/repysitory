from enum import Enum
from uuid import UUID, uuid4

import pydantic
from pydantic import BaseModel


class BaseEntity(BaseModel):
    """Base entity class for all database models."""

    model_config = pydantic.ConfigDict(use_enum_values=True, extra="ignore")
    id: UUID = uuid4()


# Sorting functionality
class SortOrder(str, Enum):
    ASC = "ASC"
    DESC = "DESC"

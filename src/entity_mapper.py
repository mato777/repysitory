from typing import Any

from pydantic import BaseModel


class EntityMapper[T: BaseModel]:
    """Composition class for entity mapping operations"""

    def __init__(self, entity_class: type[T]):
        self.entity_class = entity_class

    def map_row_to_entity(self, row: Any) -> T:
        """Map database row to entity"""
        return self.entity_class(**dict(row))

    def map_rows_to_entities(self, rows: list[Any]) -> list[T]:
        """Map database rows to entities"""
        return [self.map_row_to_entity(row) for row in rows]

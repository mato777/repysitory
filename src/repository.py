from typing import TypeVar
from uuid import UUID

import asyncpg
from pydantic import BaseModel

from src.db_context import DatabaseManager
from src.query_builder import QueryBuilder

T = TypeVar("T", bound=BaseModel)  # Entity type
S = TypeVar("S", bound=BaseModel)  # Search model type
U = TypeVar("U", bound=BaseModel)  # Update model type


class Repository[T: BaseModel, S: BaseModel, U: BaseModel]:
    entity_class: type[T]
    search_class: type[S]
    update_class: type[U]
    table_name: str

    def __init__(
        self,
        entity_class: type[T],
        search_class: type[S],
        update_class: type[U],
        table_name: str,
    ):
        self.entity_class = entity_class
        self.search_class = search_class
        self.update_class = update_class
        self.table_name = table_name

    def _build_order_clause(self, sort_model: BaseModel | None) -> str:
        """Build ORDER BY clause from sort model"""
        if not sort_model:
            return ""

        sort_dict = {k: v for k, v in sort_model.model_dump().items() if v is not None}
        if not sort_dict:
            return ""

        order_parts = []
        for field, order in sort_dict.items():
            order_parts.append(f"{field} {order}")

        return ", ".join(order_parts)

    @staticmethod
    def _get_connection() -> asyncpg.Connection:
        """Get the current database connection from context"""
        conn = DatabaseManager.get_current_connection()
        if not conn:
            raise ValueError(
                "No active transaction found. Repository methods must be called within a transaction context."
            )
        return conn

    def _apply_search_conditions(
        self, builder: QueryBuilder, search: S
    ) -> QueryBuilder:
        """Apply search conditions to the query builder"""
        search_dict = {k: v for k, v in search.model_dump().items() if v is not None}

        for field, value in search_dict.items():
            builder = builder.where(field, value)

        return builder

    async def find_by_id(self, entity_id: UUID) -> T | None:
        conn = self._get_connection()

        query, params = (
            QueryBuilder(self.table_name).where("id", str(entity_id)).build()
        )

        row = await conn.fetchrow(query, *params)
        if row:
            return self.entity_class(**dict(row))
        return None

    async def find_one_by(self, search: S) -> T | None:
        conn = self._get_connection()

        search_dict = {k: v for k, v in search.model_dump().items() if v is not None}
        if not search_dict:
            return None

        builder = QueryBuilder(self.table_name)
        builder = self._apply_search_conditions(builder, search)
        query, params = builder.build()

        row = await conn.fetchrow(query, *params)
        if row:
            return self.entity_class(**dict(row))
        return None

    async def find_many_by(
        self, search: S | None = None, sort: BaseModel | None = None
    ) -> list[T]:
        conn = self._get_connection()

        builder = QueryBuilder(self.table_name)

        if search:
            builder = self._apply_search_conditions(builder, search)

        # Add ORDER BY clause if sort is provided
        order_clause = self._build_order_clause(sort)
        if order_clause:
            builder = builder.order_by(order_clause)

        query, params = builder.build()
        rows = await conn.fetch(query, *params)
        return [self.entity_class(**dict(row)) for row in rows]

    async def create(self, entity: T) -> T:
        conn = self._get_connection()

        fields = entity.model_dump()
        columns = ", ".join(fields.keys())
        values = list(fields.values())
        placeholders = ", ".join([f"${i + 1}" for i in range(len(values))])

        await conn.execute(
            f"INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders})",
            *values,
        )
        return entity

    async def create_many(self, entities: list[T]) -> list[T]:
        conn = self._get_connection()
        if not entities:
            return []

        fields = entities[0].model_dump().keys()
        columns = ", ".join(fields)

        field_count = len(fields)
        rows_placeholders = []
        all_values = []

        for i, entity in enumerate(entities):
            entity_values = list(entity.model_dump().values())
            all_values.extend(entity_values)

            row_placeholders = ", ".join(
                [f"${j + i * field_count + 1}" for j in range(field_count)]
            )
            rows_placeholders.append(f"({row_placeholders})")

        values_clause = ", ".join(rows_placeholders)

        await conn.execute(
            f"INSERT INTO {self.table_name} ({columns}) VALUES {values_clause}",
            *all_values,
        )
        return entities

    async def update(self, entity_id: UUID, update_data: U) -> T | None:
        conn = self._get_connection()

        update_dict = {
            k: v for k, v in update_data.model_dump().items() if v is not None
        }

        if not update_dict:
            return await self.find_by_id(entity_id)

        set_clause = ", ".join(
            [f"{k} = ${i + 2}" for i, k in enumerate(update_dict.keys())]
        )
        values = list(update_dict.values())
        values.insert(0, str(entity_id))

        await conn.execute(
            f"UPDATE {self.table_name} SET {set_clause} WHERE id = $1", *values
        )

        # Use QueryBuilder for the SELECT query
        query, params = (
            QueryBuilder(self.table_name).where("id", str(entity_id)).build()
        )

        row = await conn.fetchrow(query, *params)
        if row:
            return self.entity_class(**dict(row))
        return None

    async def delete(self, entity_id: UUID) -> bool:
        conn = self._get_connection()

        result = await conn.execute(
            f"DELETE FROM {self.table_name} WHERE id = $1", str(entity_id)
        )
        return result != "DELETE 0"

    async def delete_many(self, ids: list[UUID]) -> int:
        """Delete multiple entities by their IDs. Returns the number of deleted records."""
        conn = self._get_connection()
        if not ids:
            return 0

        str_ids = [str(entity_id) for entity_id in ids]

        placeholders = ", ".join([f"${i + 1}" for i in range(len(str_ids))])

        result = await conn.execute(
            f"DELETE FROM {self.table_name} WHERE id IN ({placeholders})", *str_ids
        )

        deleted_count = int(result.split()[-1]) if result != "DELETE 0" else 0
        return deleted_count

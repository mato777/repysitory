import asyncpg
from typing import Generic, TypeVar, List, Optional, Dict, Any, Type
from uuid import UUID
from pydantic import BaseModel
from src.db_context import DatabaseManager

T = TypeVar('T', bound=BaseModel)  # Entity type
S = TypeVar('S', bound=BaseModel)  # Search model type
U = TypeVar('U', bound=BaseModel)  # Update model type

class Repository(Generic[T, S, U]):  # Now requires entity, search, and update types
    entity_class: Type[T]
    search_class: Type[S]
    update_class: Type[U]
    table_name: str

    def __init__(self, entity_class: Type[T], search_class: Type[S], update_class: Type[U], table_name: str):
        self.entity_class = entity_class
        self.search_class = search_class
        self.update_class = update_class
        self.table_name = table_name

    def _build_order_clause(self, sort_model: Optional[BaseModel]) -> str:
        """Build ORDER BY clause from sort model"""
        if not sort_model:
            return ""

        sort_dict = {k: v for k, v in sort_model.model_dump().items() if v is not None}
        if not sort_dict:
            return ""

        order_parts = []
        for field, order in sort_dict.items():
            order_parts.append(f"{field} {order}")

        return f" ORDER BY {', '.join(order_parts)}"

    def _get_connection(self) -> asyncpg.Connection:
        """Get the current database connection from context"""
        conn = DatabaseManager.get_current_connection()
        if not conn:
            raise ValueError("No active transaction found. Repository methods must be called within a transaction context.")
        return conn

    async def find_by_id(self, id: UUID) -> Optional[T]:
        conn = self._get_connection()
        row = await conn.fetchrow(f"SELECT * FROM {self.table_name} WHERE id = $1", str(id))
        if row:
            return self.entity_class(**dict(row))
        return None

    async def find_one_by(self, search: S) -> Optional[T]:
        conn = self._get_connection()

        # Convert search model to dict and filter out None values
        search_dict = {k: v for k, v in search.model_dump().items() if v is not None}

        if not search_dict:
            return None

        keys = list(search_dict.keys())
        values = list(search_dict.values())
        where_clause = ' AND '.join([f"{k} = ${i+1}" for i, k in enumerate(keys)])
        row = await conn.fetchrow(f"SELECT * FROM {self.table_name} WHERE {where_clause}", *values)
        if row:
            return self.entity_class(**dict(row))
        return None

    async def find_many_by(self, search: Optional[S] = None, sort: Optional[BaseModel] = None) -> List[T]:
        conn = self._get_connection()

        if not search:
            query = f"SELECT * FROM {self.table_name}"
            values = []
        else:
            # Convert search model to dict and filter out None values
            search_dict = {k: v for k, v in search.model_dump().items() if v is not None}

            if not search_dict:
                query = f"SELECT * FROM {self.table_name}"
                values = []
            else:
                keys = list(search_dict.keys())
                values = list(search_dict.values())
                where_clause = ' AND '.join([f"{k} = ${i+1}" for i, k in enumerate(keys)])
                query = f"SELECT * FROM {self.table_name} WHERE {where_clause}"

        # Add ORDER BY clause
        order_clause = self._build_order_clause(sort)
        query += order_clause

        rows = await conn.fetch(query, *values)
        return [self.entity_class(**dict(row)) for row in rows]

    async def create(self, entity: T) -> T:
        conn = self._get_connection()

        fields = entity.model_dump()
        columns = ', '.join(fields.keys())
        values = list(fields.values())
        placeholders = ', '.join([f"${i+1}" for i in range(len(values))])

        await conn.execute(
            f"INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders})",
            *values
        )
        return entity

    async def create_many(self, entities: List[T]) -> List[T]:
        conn = self._get_connection()
        if not entities:
            return []

        fields = entities[0].model_dump().keys()
        columns = ', '.join(fields)

        # Create placeholders for multiple rows
        # Each row needs placeholders like ($1, $2, $3), ($4, $5, $6), etc.
        field_count = len(fields)
        rows_placeholders = []
        all_values = []

        for i, entity in enumerate(entities):
            entity_values = list(entity.model_dump().values())
            all_values.extend(entity_values)

            # Create placeholders for this row: ($1, $2, $3) for first row, ($4, $5, $6) for second, etc.
            row_placeholders = ', '.join([f"${j + i * field_count + 1}" for j in range(field_count)])
            rows_placeholders.append(f"({row_placeholders})")

        # Join all row placeholders: ($1, $2, $3), ($4, $5, $6), ...
        values_clause = ', '.join(rows_placeholders)

        await conn.execute(
            f"INSERT INTO {self.table_name} ({columns}) VALUES {values_clause}",
            *all_values
        )
        return entities

    async def update(self, id: UUID, update_data: U) -> Optional[T]:
        conn = self._get_connection()

        # Convert update model to dict and filter out None values
        update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}

        if not update_dict:
            return await self.find_by_id(id)

        set_clause = ', '.join([f"{k} = ${i+2}" for i, k in enumerate(update_dict.keys())])
        values = list(update_dict.values())
        values.insert(0, str(id))

        await conn.execute(
            f"UPDATE {self.table_name} SET {set_clause} WHERE id = $1",
            *values
        )
        row = await conn.fetchrow(f"SELECT * FROM {self.table_name} WHERE id = $1", str(id))
        if row:
            return self.entity_class(**dict(row))
        return None

    async def delete(self, id: UUID) -> bool:
        conn = self._get_connection()

        result = await conn.execute(f"DELETE FROM {self.table_name} WHERE id = $1", str(id))
        return result != "DELETE 0"

    async def delete_many(self, ids: List[UUID]) -> int:
        """Delete multiple entities by their IDs. Returns the number of deleted records."""
        conn = self._get_connection()
        if not ids:
            return 0

        # Convert UUIDs to strings for the query
        str_ids = [str(id) for id in ids]

        # Create placeholders for the IN clause: $1, $2, $3, ...
        placeholders = ', '.join([f"${i+1}" for i in range(len(str_ids))])

        result = await conn.execute(
            f"DELETE FROM {self.table_name} WHERE id IN ({placeholders})",
            *str_ids
        )

        # Extract the number of deleted rows from the result
        # Result format is "DELETE n" where n is the number of deleted rows
        deleted_count = int(result.split()[-1]) if result != "DELETE 0" else 0
        return deleted_count

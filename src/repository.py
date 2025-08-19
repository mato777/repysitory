from typing import Any, TypeVar
from uuid import UUID

from pydantic import BaseModel

from src.database_operations import DatabaseOperations
from src.entity_mapper import EntityMapper
from src.query_builder import QueryBuilder
from src.search_condition_builder import SearchConditionBuilder

T = TypeVar("T", bound=BaseModel)  # Entity type
S = TypeVar("S", bound=BaseModel)  # Search model type
U = TypeVar("U", bound=BaseModel)  # Update model type


class Repository[T: BaseModel, S: BaseModel, U: BaseModel]:
    """Repository class using composition and inheritance"""

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
        self._query_builder: QueryBuilder | None = None

        # Composition: Inject dependencies
        self.db_ops = DatabaseOperations()
        self.entity_mapper = EntityMapper(entity_class)
        self.search_builder = SearchConditionBuilder()

    def _get_or_create_query_builder(self) -> QueryBuilder:
        """Get existing query builder or create a new one"""
        if self._query_builder is None:
            return QueryBuilder(self.table_name)
        return self._query_builder

    def _clone_with_query_builder(
        self, query_builder: QueryBuilder
    ) -> "Repository[T, S, U]":
        """Create a new repository instance with the given query builder"""
        new_repo = Repository(
            self.entity_class, self.search_class, self.update_class, self.table_name
        )
        new_repo._query_builder = query_builder
        return new_repo

    # Fluent query methods that return a new repository instance
    def select(self, fields: str = "*") -> "Repository[T, S, U]":
        """Set the SELECT fields"""
        current_builder = self._get_or_create_query_builder()
        new_builder = current_builder.select(fields)
        return self._clone_with_query_builder(new_builder)

    def where(
        self, field: str, *args: Any
    ) -> "Repository[T, S, U]":
        """Add a WHERE condition.

        Supports both: where(field, value) and where(field, operator, value)
        """
        current_builder = self._get_or_create_query_builder()
        new_builder = current_builder.where(field, *args)
        return self._clone_with_query_builder(new_builder)

    def or_where(
        self, field: str, *args: Any
    ) -> "Repository[T, S, U]":
        """Add an OR WHERE condition.

        Supports both: or_where(field, value) and or_where(field, operator, value)
        """
        current_builder = self._get_or_create_query_builder()
        new_builder = current_builder.or_where(field, *args)
        return self._clone_with_query_builder(new_builder)

    def where_in(self, field: str, values: list) -> "Repository[T, S, U]":
        """Add a WHERE IN condition"""
        current_builder = self._get_or_create_query_builder()
        new_builder = current_builder.where_in(field, values)
        return self._clone_with_query_builder(new_builder)

    def where_not_in(self, field: str, values: list) -> "Repository[T, S, U]":
        """Add a WHERE NOT IN condition"""
        current_builder = self._get_or_create_query_builder()
        new_builder = current_builder.where_not_in(field, values)
        return self._clone_with_query_builder(new_builder)

    def order_by(self, field: str) -> "Repository[T, S, U]":
        """Add ORDER BY ascending for a field (default)."""
        current_builder = self._get_or_create_query_builder()
        new_builder = current_builder.order_by(field)
        return self._clone_with_query_builder(new_builder)

    def order_by_asc(self, field: str) -> "Repository[T, S, U]":
        """Add ORDER BY ... ASC for a field. Can be chained for multiple fields."""
        current_builder = self._get_or_create_query_builder()
        new_builder = current_builder.order_by_asc(field)
        return self._clone_with_query_builder(new_builder)

    def order_by_desc(self, field: str) -> "Repository[T, S, U]":
        """Add ORDER BY ... DESC for a field. Can be chained for multiple fields."""
        current_builder = self._get_or_create_query_builder()
        new_builder = current_builder.order_by_desc(field)
        return self._clone_with_query_builder(new_builder)

    def limit(self, count: int) -> "Repository[T, S, U]":
        """Set the LIMIT clause"""
        current_builder = self._get_or_create_query_builder()
        new_builder = current_builder.limit(count)
        return self._clone_with_query_builder(new_builder)

    def offset(self, count: int) -> "Repository[T, S, U]":
        """Set the OFFSET clause"""
        current_builder = self._get_or_create_query_builder()
        new_builder = current_builder.offset(count)
        return self._clone_with_query_builder(new_builder)

    def paginate(self, page: int, per_page: int = 10) -> "Repository[T, S, U]":
        """Set pagination parameters"""
        current_builder = self._get_or_create_query_builder()
        new_builder = current_builder.paginate(page, per_page)
        return self._clone_with_query_builder(new_builder)

    # Execution methods for fluent queries
    async def get(self) -> list[T]:
        """Execute the query and return all matching entities"""
        if self._query_builder is None:
            self._query_builder = QueryBuilder(self.table_name)

        query, params = self._query_builder.build()
        rows = await self.db_ops.fetch_all(query, params)
        return self.entity_mapper.map_rows_to_entities(rows)

    async def first(self) -> T | None:
        """Execute the query and return the first matching entity"""
        current_builder = self._get_or_create_query_builder()
        limited_builder = current_builder.limit(1)

        query, params = limited_builder.build()
        row = await self.db_ops.fetch_one(query, params)
        if row:
            return self.entity_mapper.map_row_to_entity(row)
        return None

    async def count(self) -> int:
        """Execute the query and return the count of matching records"""
        current_builder = self._get_or_create_query_builder()
        count_builder = current_builder.select("COUNT(*)")

        query, params = count_builder.build()
        result = await self.db_ops.fetch_value(query, params)
        return result or 0

    async def exists(self) -> bool:
        """Check if any records match the query"""
        count = await self.count()
        return count > 0

    def to_sql(self) -> str:
        """Return the SQL query string for debugging"""
        current_builder = self._get_or_create_query_builder()
        return current_builder.to_sql()

    def build(self) -> tuple[str, list[Any]]:
        """Build the SQL query and parameters"""
        current_builder = self._get_or_create_query_builder()
        return current_builder.build()

    # CRUD operations - refactored to use fluent interface where possible
    async def find_by_id(self, entity_id: UUID) -> T | None:
        """Find entity by ID using fluent interface"""
        return await self.where("id", str(entity_id)).first()

    async def find_one_by(self, search: S) -> T | None:
        """Find one entity by search criteria using fluent interface"""
        search_dict = {k: v for k, v in search.model_dump().items() if v is not None}
        if not search_dict:
            return None

        # Build query using fluent interface
        query_repo = self
        for field, value in search_dict.items():
            query_repo = query_repo.where(field, value)

        return await query_repo.first()

    async def find_many_by(
        self, search: S | None = None, sort: BaseModel | None = None
    ) -> list[T]:
        """Find many entities by search criteria using fluent interface"""
        query_repo = self

        if search:
            search_dict = {
                k: v for k, v in search.model_dump().items() if v is not None
            }
            for field, value in search_dict.items():
                query_repo = query_repo.where(field, value)

        # Apply ORDER BY if sort is provided (ASC by default, DESC via order_by_desc)
        query_repo = self._clone_with_query_builder(
            self.search_builder.apply_sort(query_repo._get_or_create_query_builder(), sort)
        )

        return await query_repo.get()

    async def create(self, entity: T) -> T:
        """Create a new entity"""
        fields = entity.model_dump()
        columns = ", ".join(fields.keys())
        values = list(fields.values())
        placeholders = ", ".join([f"${i + 1}" for i in range(len(values))])

        await self.db_ops.execute_query(
            f"INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders})",
            values,
        )
        return entity

    async def create_many(self, entities: list[T]) -> list[T]:
        """Create multiple entities"""
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

        await self.db_ops.execute_query(
            f"INSERT INTO {self.table_name} ({columns}) VALUES {values_clause}",
            all_values,
        )
        return entities

    async def update(self, entity_id: UUID, update_data: U) -> T | None:
        """Update entity and return updated version using fluent interface"""
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

        await self.db_ops.execute_query(
            f"UPDATE {self.table_name} SET {set_clause} WHERE id = $1", values
        )

        # Use fluent interface to fetch updated entity
        return await self.find_by_id(entity_id)

    async def delete(self, entity_id: UUID) -> bool:
        """Delete entity by ID"""
        result = await self.db_ops.execute_query(
            f"DELETE FROM {self.table_name} WHERE id = $1", [str(entity_id)]
        )
        return result != "DELETE 0"

    async def delete_many(self, ids: list[UUID]) -> int:
        """Delete multiple entities by their IDs using fluent interface"""
        if not ids:
            return 0

        str_ids = [str(entity_id) for entity_id in ids]

        # Could potentially use fluent interface: self.where_in("id", str_ids).delete()
        # But keeping direct implementation for now
        placeholders = ", ".join([f"${i + 1}" for i in range(len(str_ids))])

        result = await self.db_ops.execute_query(
            f"DELETE FROM {self.table_name} WHERE id IN ({placeholders})", str_ids
        )

        deleted_count = int(result.split()[-1]) if result != "DELETE 0" else 0
        return deleted_count

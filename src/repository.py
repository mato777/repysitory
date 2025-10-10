"""Repository class"""

from typing import Any, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from src.database_operations import DatabaseOperations
from src.entity_mapper import EntityMapper
from src.features.base_feature import RepositoryFeature
from src.features.timestamp_feature import TimestampFeature
from src.query_builder import QueryBuilder
from src.search_condition_builder import SearchConditionBuilder

T = TypeVar("T", bound=BaseModel)  # Entity type
S = TypeVar("S", bound=BaseModel)  # Search model type
U = TypeVar("U", bound=BaseModel)  # Update model type


class RepositoryConfig(BaseModel):
    """Configuration options for Repository"""

    model_config = {"arbitrary_types_allowed": True}

    db_schema: str | None = Field(default=None, description="Database schema name")
    timestamps: bool = Field(
        default=False,
        description="Enable automatic timestamp management (backward compatibility)",
    )
    features: list[RepositoryFeature] = Field(
        default_factory=list, description="List of repository features to enable"
    )

    @model_validator(mode="after")
    def setup_features(self) -> "RepositoryConfig":
        """Auto-create TimestampFeature if timestamps=True for backward compatibility"""
        if self.timestamps and not any(
            isinstance(f, TimestampFeature) for f in self.features
        ):
            self.features.append(TimestampFeature())
        return self


class Repository[T: BaseModel, S: BaseModel, U: BaseModel]:
    """Repository class using composition and inheritance"""

    def __init__(
        self,
        entity_class: type[T],
        search_class: type[S],
        update_class: type[U],
        table_name: str,
        config: RepositoryConfig | None = None,
    ):
        self.entity_class = entity_class
        self.search_class = search_class
        self.update_class = update_class
        self.table_name = table_name
        self.config = config or RepositoryConfig()
        self._qualified_table_name = (
            f"{self.config.db_schema}.{table_name}"
            if self.config.db_schema
            else table_name
        )
        self._query_builder: QueryBuilder | None = None

        # Soft delete state
        self._include_trashed: bool = False
        self._only_trashed: bool = False

        # Apply features to augment entity class
        self._entity_class_with_features = entity_class
        for feature in self.config.features:
            self._entity_class_with_features = feature.augment_entity_class(
                self._entity_class_with_features
            )

        # Composition: Inject dependencies
        self.db_ops = DatabaseOperations()
        self.entity_mapper = EntityMapper(self._entity_class_with_features)
        self.search_builder = SearchConditionBuilder()

    def _get_or_create_query_builder(self) -> QueryBuilder:
        """Get an existing query builder or create a new one"""
        if self._query_builder is None:
            return QueryBuilder(self._qualified_table_name)
        return self._query_builder

    def _clone_with_query_builder(
        self, query_builder: QueryBuilder
    ) -> "Repository[T, S, U]":
        """Create a new repository instance with the given query builder"""
        new_repo = Repository(
            self.entity_class,
            self.search_class,
            self.update_class,
            self.table_name,
            self.config,
        )
        new_repo._query_builder = query_builder
        # Preserve the soft delete state
        new_repo._include_trashed = self._include_trashed
        new_repo._only_trashed = self._only_trashed
        return new_repo

    def _has_soft_delete_feature(self) -> bool:
        """Check if the soft delete feature is enabled"""
        from src.features.soft_delete_feature import SoftDeleteFeature

        return any(isinstance(f, SoftDeleteFeature) for f in self.config.features)

    def _get_soft_delete_feature(self):
        """Get the soft delete feature instance if enabled"""
        from src.features.soft_delete_feature import SoftDeleteFeature

        for feature in self.config.features:
            if isinstance(feature, SoftDeleteFeature):
                return feature
        return None

    def _apply_feature_hooks(
        self, data: dict[str, Any], is_create: bool = True
    ) -> dict[str, Any]:
        """Apply feature hooks to data (before creation or update)"""
        for feature in self.config.features:
            if is_create:
                data = feature.before_create(data)
            else:
                data = feature.before_update(data)
        return data

    # Fluent query methods that return a new repository instance
    def select(self, *fields: str) -> "Repository[T, S, U]":
        """Set the SELECT fields. Accepts one or more field strings; defaults to * when none is provided."""
        current_builder = self._get_or_create_query_builder()
        new_builder = current_builder.select(*fields)
        return self._clone_with_query_builder(new_builder)

    def where(self, field: str, *args: Any) -> "Repository[T, S, U]":
        """Add a WHERE condition.

        Supports both: where(field, value) and where (field, operator, value)
        """
        current_builder = self._get_or_create_query_builder()
        new_builder = current_builder.where(field, *args)
        return self._clone_with_query_builder(new_builder)

    def or_where(self, field: str, *args: Any) -> "Repository[T, S, U]":
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

    def group_by(self, *fields: str) -> "Repository[T, S, U]":
        """Add GROUP BY fields."""
        current_builder = self._get_or_create_query_builder()
        new_builder = current_builder.group_by(*fields)
        return self._clone_with_query_builder(new_builder)

    def having(self, field: str, *args: Any) -> "Repository[T, S, U]":
        """Add a HAVING condition. Supports (field, value) or (field, operator, value)."""
        current_builder = self._get_or_create_query_builder()
        new_builder = current_builder.having(field, *args)
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

    def with_trashed(self) -> "Repository[T, S, U]":
        """Include soft-deleted records in query results (only if soft delete is enabled)"""
        new_repo = self._clone_with_query_builder(self._get_or_create_query_builder())
        new_repo._include_trashed = True
        new_repo._only_trashed = False
        return new_repo

    def only_trashed(self) -> "Repository[T, S, U]":
        """Only return soft-deleted records (only if soft delete is enabled)"""
        new_repo = self._clone_with_query_builder(self._get_or_create_query_builder())
        new_repo._include_trashed = False
        new_repo._only_trashed = True
        return new_repo

    # Execution methods for fluent queries
    async def get(self) -> list[T]:
        """Execute the query and return all matching entities"""
        if self._query_builder is None:
            self._query_builder = QueryBuilder(self._qualified_table_name)

        # Apply soft delete filters if enabled
        query_builder = self._query_builder
        if self._has_soft_delete_feature():
            if self._only_trashed:
                # Only return soft-deleted records (deleted_at IS NOT NULL)
                query_builder = query_builder.where("deleted_at", "!=", None)
            elif not self._include_trashed:
                # Exclude soft-deleted records (deleted_at IS NULL)
                query_builder = query_builder.where("deleted_at", None)

        query, params = query_builder.build()
        rows = await self.db_ops.fetch_all(query, params)

        # If custom SELECT fields are used (not '*'), return raw rows as dictionaries
        if self._query_builder.select_fields.strip() != "*":
            return [dict(row) for row in rows]  # type: ignore[return-value]

        return self.entity_mapper.map_rows_to_entities(rows)  # type: ignore[return-value]

    async def first(self) -> T | None:
        """Execute the query and return the first matching entity"""
        current_builder = self._get_or_create_query_builder()

        # Apply soft delete filters if enabled
        if self._has_soft_delete_feature():
            if self._only_trashed:
                # Only return soft-deleted records (deleted_at IS NOT NULL)
                current_builder = current_builder.where("deleted_at", "!=", None)
            elif not self._include_trashed:
                # Exclude soft-deleted records (deleted_at IS NULL)
                current_builder = current_builder.where("deleted_at", None)

        limited_builder = current_builder.limit(1)

        query, params = limited_builder.build()
        row = await self.db_ops.fetch_one(query, params)
        if row:
            return self.entity_mapper.map_row_to_entity(row)  # type: ignore[return-value]
        return None

    async def count(self) -> int:
        """Execute the query and return the count of matching records"""
        current_builder = self._get_or_create_query_builder()

        # Apply soft delete filters if enabled
        if self._has_soft_delete_feature():
            if self._only_trashed:
                # Only count soft-deleted records (deleted_at IS NOT NULL)
                current_builder = current_builder.where("deleted_at", "!=", None)
            elif not self._include_trashed:
                # Exclude soft-deleted records (deleted_at IS NULL)
                current_builder = current_builder.where("deleted_at", None)

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
        """Find one entity by search criteria using a fluent interface"""
        # Use exclude_unset to include explicit None values in search
        search_dict = search.model_dump(exclude_unset=True)
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
        """Find many entities by search criteria using a fluent interface"""
        query_repo = self

        if search:
            # Use exclude_unset to include explicit None values in search
            search_dict = search.model_dump(exclude_unset=True)
            for field, value in search_dict.items():
                query_repo = query_repo.where(field, value)

        # Apply ORDER BY if a sort is provided (ASC by default, DESC via order_by_desc)
        query_repo = self._clone_with_query_builder(
            self.search_builder.apply_sort(
                query_repo._get_or_create_query_builder(), sort
            )
        )

        return await query_repo.get()

    async def create(self, entity: T) -> T:
        """Create a new entity"""
        fields = entity.model_dump()
        fields = self._apply_feature_hooks(fields, is_create=True)

        columns = ", ".join(fields.keys())
        values = list(fields.values())
        placeholders = ", ".join([f"${i + 1}" for i in range(len(values))])

        await self.db_ops.execute_query(
            f"INSERT INTO {self._qualified_table_name} ({columns}) VALUES ({placeholders})",
            values,
        )

        # Return entity with features applied
        return self._entity_class_with_features(**fields)  # type: ignore[return-value]

    async def create_many(self, entities: list[T]) -> list[T]:
        """Create multiple entities"""
        if not entities:
            return []

        # Process the first entity to get field structure
        first_entity_fields = entities[0].model_dump()
        first_entity_fields = self._apply_feature_hooks(
            first_entity_fields, is_create=True
        )
        fields = first_entity_fields.keys()
        columns = ", ".join(fields)

        field_count = len(fields)
        rows_placeholders = []
        all_values = []

        for i, entity in enumerate(entities):
            entity_fields = entity.model_dump()
            entity_fields = self._apply_feature_hooks(entity_fields, is_create=True)
            entity_values = list(entity_fields.values())
            all_values.extend(entity_values)

            row_placeholders = ", ".join(
                [f"${j + i * field_count + 1}" for j in range(field_count)]
            )
            rows_placeholders.append(f"({row_placeholders})")

        values_clause = ", ".join(rows_placeholders)

        await self.db_ops.execute_query(
            f"INSERT INTO {self._qualified_table_name} ({columns}) VALUES {values_clause}",
            all_values,
        )

        # Return entities with features applied
        result_entities = []
        for entity in entities:
            entity_fields = entity.model_dump()
            entity_fields = self._apply_feature_hooks(entity_fields, is_create=True)
            result_entities.append(self._entity_class_with_features(**entity_fields))

        return result_entities

    async def update(self, entity_id: UUID, update_data: U) -> T | None:
        """Update entity and return the updated version using fluent interface"""
        # Use exclude_unset to only include fields that were explicitly set.
        # This allows None values (for restoration) while excluding unset fields
        update_dict = update_data.model_dump(exclude_unset=True)
        update_dict = self._apply_feature_hooks(update_dict, is_create=False)

        if not update_dict:
            return await self.find_by_id(entity_id)

        set_clause = ", ".join(
            [f"{k} = ${i + 2}" for i, k in enumerate(update_dict.keys())]
        )
        values = list(update_dict.values())
        values.insert(0, str(entity_id))

        await self.db_ops.execute_query(
            f"UPDATE {self._qualified_table_name} SET {set_clause} WHERE id = $1",
            values,
        )

        # Use fluent interface to fetch an updated entity
        return await self.find_by_id(entity_id)

    async def update_many_by_ids(self, ids: list[UUID], update_data: U) -> list[T]:
        """Update multiple entities by their IDs with the same changes and return the updated entities."""
        if not ids:
            return []

        # Use exclude_unset to only include fields that were explicitly set.
        # This allows None values (for restoration) while excluding unset fields
        update_dict = update_data.model_dump(exclude_unset=True)
        update_dict = self._apply_feature_hooks(update_dict, is_create=False)

        if not update_dict:
            # Nothing to update
            return []

        # SET clauses start at $1.$m
        set_clause = ", ".join(
            [f"{k} = ${i + 1}" for i, k in enumerate(update_dict.keys())]
        )

        # WHERE id IN placeholders continue after the SET params
        str_ids = [str(entity_id) for entity_id in ids]
        ids_placeholders = ", ".join(
            [f"${len(update_dict) + i + 1}" for i in range(len(str_ids))]
        )

        sql = (
            f"UPDATE {self._qualified_table_name} SET {set_clause} "
            f"WHERE id IN ({ids_placeholders}) RETURNING *"
        )
        params = list(update_dict.values()) + str_ids

        rows = await self.db_ops.fetch_all(sql, params)
        return self.entity_mapper.map_rows_to_entities(rows)  # type: ignore[return-value]

    async def delete(self, entity_id: UUID | None = None) -> bool | int:
        """
        Delete entity by ID or delete all records matching the current query.

        - repo.delete(id) -> Delete a single entity by ID, returns bool
        - repo.where(...).delete() -> Delete all matching records, returns count

        Performs soft delete if the feature is enabled, hard delete otherwise.
        """
        # If entity_id provided, delete single entity
        if entity_id is not None:
            if self._has_soft_delete_feature():
                # Softly delete: set deleted_at to the current timestamp
                from datetime import UTC, datetime

                deleted_at = datetime.now(UTC)

                result = await self.db_ops.execute_query(
                    f"UPDATE {self._qualified_table_name} SET deleted_at = $2 WHERE id = $1",
                    [str(entity_id), deleted_at],
                )
                return result != "UPDATE 0"
            else:
                # Hard delete: actually remove from a database
                result = await self.db_ops.execute_query(
                    f"DELETE FROM {self._qualified_table_name} WHERE id = $1",
                    [str(entity_id)],
                )
                return result != "DELETE 0"

        # Otherwise, delete it based on query builder conditions
        if self._query_builder is None:
            raise ValueError("Cannot delete without entity_id or WHERE conditions")

        if (
            self._query_builder.where_conditions
            or self._query_builder.or_where_conditions
        ):
            all_conditions = []
            if self._query_builder.where_conditions:
                all_conditions.append(
                    " AND ".join(self._query_builder.where_conditions)
                )
            if self._query_builder.or_where_conditions:
                all_conditions.append(
                    " OR ".join(self._query_builder.or_where_conditions)
                )
            where_clause = " WHERE " + " AND ".join(
                f"({cond})" for cond in all_conditions
            )
            params = self._query_builder.params.copy()
        else:
            raise ValueError("Cannot delete without WHERE conditions")

        if self._has_soft_delete_feature():
            # Softly delete: set deleted_at for all matching records
            import re
            from datetime import UTC, datetime

            deleted_at = datetime.now(UTC)

            # Adjust parameter indices in the WHERE clause (increment by 1 for deleted_at at $1)
            def adjust_param_index(match):
                param_num = int(match.group(1))
                return f"${param_num + 1}"

            adjusted_where_clause = re.sub(r"\$(\d+)", adjust_param_index, where_clause)

            # Add the deleted_at parameter at the beginning
            params.insert(0, deleted_at)

            result = await self.db_ops.execute_query(
                f"UPDATE {self._qualified_table_name} SET deleted_at = $1{adjusted_where_clause}",
                params,
            )
            # Extract count from "UPDATE N" result
            return int(result.split()[-1]) if result != "UPDATE 0" else 0
        else:
            # Hard delete
            result = await self.db_ops.execute_query(
                f"DELETE FROM {self._qualified_table_name}{where_clause}", params
            )
            return int(result.split()[-1]) if result != "DELETE 0" else 0

    async def force_delete(self, entity_id: UUID) -> bool:
        """Permanently delete entity by ID (hard delete), bypassing soft delete"""
        result = await self.db_ops.execute_query(
            f"DELETE FROM {self._qualified_table_name} WHERE id = $1", [str(entity_id)]
        )
        return result != "DELETE 0"

    async def restore(self, entity_id: UUID) -> T | None:
        """Restore a soft-deleted entity by setting deleted_at to None"""
        if not self._has_soft_delete_feature():
            # Can't restore if soft delete is not enabled
            return None

        result = await self.db_ops.execute_query(
            f"UPDATE {self._qualified_table_name} SET deleted_at = NULL WHERE id = $1",
            [str(entity_id)],
        )

        if result == "UPDATE 0":
            return None

        # Return the restored entity
        return await self.with_trashed().find_by_id(entity_id)

    async def delete_many(self, ids: list[UUID]) -> int:
        """Delete multiple entities by their IDs using a fluent interface"""
        if not ids:
            return 0

        str_ids = [str(entity_id) for entity_id in ids]

        # Could potentially use a fluent interface: self.where_in("id", str_ids).delete()
        # But keeping direct implementation for now
        placeholders = ", ".join([f"${i + 1}" for i in range(len(str_ids))])

        result = await self.db_ops.execute_query(
            f"DELETE FROM {self._qualified_table_name} WHERE id IN ({placeholders})",
            str_ids,
        )

        deleted_count = int(result.split()[-1]) if result != "DELETE 0" else 0
        return deleted_count

"""
Simple QueryBuilder for building SELECT queries.
The goal is to produce SQL queries without execution.
"""

from collections.abc import Callable
from typing import Any


class QueryBuilder:
    """
    Simple query builder for SELECT statements.

    Usage:
        builder = QueryBuilder("posts")
        query, params = builder.select("*").where("id", post_id).build()
    """

    def __init__(self, table_name: str):
        self.table_name = table_name
        self.select_fields = "*"
        self.where_conditions: list[str] = []
        self.or_where_conditions: list[str] = []
        self.params: list[Any] = []
        self.order_by_clause = ""

    def _clone(self) -> "QueryBuilder":
        """Create a copy of the current QueryBuilder instance"""
        new_builder = QueryBuilder(self.table_name)
        new_builder.select_fields = self.select_fields
        new_builder.where_conditions = self.where_conditions.copy()
        new_builder.or_where_conditions = self.or_where_conditions.copy()
        new_builder.params = self.params.copy()
        new_builder.order_by_clause = self.order_by_clause
        return new_builder

    def _add_condition(
        self, field: str, value: Any, operator: str, is_or: bool = False
    ) -> "QueryBuilder":
        """Add a condition to either WHERE or OR WHERE clauses"""
        new_builder = self._clone()
        param_index = len(new_builder.params) + 1
        condition = f"{field} {operator} ${param_index}"

        if is_or:
            new_builder.or_where_conditions.append(condition)
        else:
            new_builder.where_conditions.append(condition)

        new_builder.params.append(value)
        return new_builder

    def _add_in_condition(
        self,
        field: str,
        values: Any | list[Any],
        is_not: bool = False,
        is_or: bool = False,
    ) -> "QueryBuilder":
        """Add IN or NOT IN conditions"""
        new_builder = self._clone()

        # Convert single value to list for consistent handling
        if not isinstance(values, list):
            values = [values]

        # Build placeholders for the IN clause
        start_index = len(new_builder.params) + 1
        placeholders = ", ".join([f"${i + start_index}" for i in range(len(values))])
        not_keyword = "NOT " if is_not else ""
        condition = f"{field} {not_keyword}IN ({placeholders})"

        if is_or:
            new_builder.or_where_conditions.append(condition)
        else:
            new_builder.where_conditions.append(condition)

        new_builder.params.extend(values)
        return new_builder

    def _build_group_condition(self, group_builder: "QueryBuilder") -> str:
        """Build a grouped condition string from a group builder"""
        adjusted_where = []
        adjusted_or_where = []
        param_offset = len(self.params)

        # Adjust parameter indices for group conditions
        for condition in group_builder.where_conditions:
            adjusted_where.append(
                self._adjust_parameter_indices(
                    condition, param_offset, len(group_builder.params)
                )
            )

        for condition in group_builder.or_where_conditions:
            adjusted_or_where.append(
                self._adjust_parameter_indices(
                    condition, param_offset, len(group_builder.params)
                )
            )

        # Build the final group condition
        if adjusted_where and adjusted_or_where:
            # Mixed AND and OR conditions
            and_clause = (
                " AND ".join(adjusted_where)
                if len(adjusted_where) > 1
                else adjusted_where[0]
            )
            or_clause = (
                " OR ".join(adjusted_or_where)
                if len(adjusted_or_where) > 1
                else adjusted_or_where[0]
            )
            return f"{and_clause} OR {or_clause}"
        elif adjusted_or_where:
            # Only OR conditions
            return " OR ".join(adjusted_or_where)
        else:
            # Only AND conditions
            return " AND ".join(adjusted_where)

    @staticmethod
    def _adjust_parameter_indices(
        condition: str, param_offset: int, total_group_params: int
    ) -> str:
        """Adjust parameter indices in a condition string"""
        adjusted_condition = condition
        # Replace in reverse order to avoid double replacements
        for i in reversed(range(total_group_params)):
            old_param = f"${i + 1}"
            new_param = f"${param_offset + i + 1}"
            adjusted_condition = adjusted_condition.replace(old_param, new_param)
        return adjusted_condition

    def select(self, fields: str) -> "QueryBuilder":
        """Set the SELECT fields"""
        new_builder = self._clone()
        new_builder.select_fields = fields
        return new_builder

    def where(
        self,
        field_or_function: str | Callable[["QueryBuilder"], "QueryBuilder"],
        value: Any = None,
        operator: str = "=",
    ) -> "QueryBuilder":
        """Add a WHERE condition or grouped WHERE clause"""
        if callable(field_or_function):
            return self.where_group(field_or_function)
        return self._add_condition(field_or_function, value, operator, is_or=False)

    def or_where(
        self,
        field_or_function: str | Callable[["QueryBuilder"], "QueryBuilder"],
        value: Any = None,
        operator: str = "=",
    ) -> "QueryBuilder":
        """Add an OR WHERE condition or grouped OR WHERE clause"""
        if callable(field_or_function):
            return self.or_where_group(field_or_function)
        return self._add_condition(field_or_function, value, operator, is_or=True)

    def where_multiple(self, conditions: list[tuple[str, Any, str]]) -> "QueryBuilder":
        """Add multiple WHERE conditions from a list of (field, value, operator) tuples"""
        new_builder = self._clone()
        for field, value, operator in conditions:
            new_builder = new_builder._add_condition(
                field, value, operator, is_or=False
            )
        return new_builder

    def or_where_multiple(
        self, conditions: list[tuple[str, Any, str]]
    ) -> "QueryBuilder":
        """Add multiple OR WHERE conditions from a list of (field, value, operator) tuples"""
        new_builder = self._clone()
        for field, value, operator in conditions:
            new_builder = new_builder._add_condition(field, value, operator, is_or=True)
        return new_builder

    def where_any(
        self, conditions: tuple[str, Any, str] | list[tuple[str, Any, str]]
    ) -> "QueryBuilder":
        """Add WHERE condition(s) - accepts either a single tuple or list of tuples"""
        if isinstance(conditions, tuple):
            field, value, operator = conditions
            return self.where(field, value, operator)
        return self.where_multiple(conditions)

    def or_where_any(
        self, conditions: tuple[str, Any, str] | list[tuple[str, Any, str]]
    ) -> "QueryBuilder":
        """Add OR WHERE condition(s) - accepts either a single tuple or list of tuples"""
        if isinstance(conditions, tuple):
            field, value, operator = conditions
            return self.or_where(field, value, operator)
        return self.or_where_multiple(conditions)

    def where_in(self, field: str, values: Any | list[Any]) -> "QueryBuilder":
        """Add a WHERE IN condition"""
        return self._add_in_condition(field, values, is_not=False, is_or=False)

    def where_not_in(self, field: str, values: Any | list[Any]) -> "QueryBuilder":
        """Add a WHERE NOT IN condition"""
        return self._add_in_condition(field, values, is_not=True, is_or=False)

    def or_where_in(self, field: str, values: Any | list[Any]) -> "QueryBuilder":
        """Add an OR WHERE IN condition"""
        return self._add_in_condition(field, values, is_not=False, is_or=True)

    def or_where_not_in(self, field: str, values: Any | list[Any]) -> "QueryBuilder":
        """Add an OR WHERE NOT IN condition"""
        return self._add_in_condition(field, values, is_not=True, is_or=True)

    def _add_group_condition(
        self,
        group_function: Callable[["QueryBuilder"], "QueryBuilder"],
        is_or: bool = False,
    ) -> "QueryBuilder":
        """Add a grouped condition to either WHERE or OR WHERE clauses"""
        group_builder = QueryBuilder("")
        result = group_function(group_builder)
        if result is not None:
            group_builder = result

        if not group_builder.where_conditions and not group_builder.or_where_conditions:
            return self

        new_builder = self._clone()
        group_condition = self._build_group_condition(group_builder)

        if is_or:
            new_builder.or_where_conditions.append(f"({group_condition})")
        else:
            new_builder.where_conditions.append(f"({group_condition})")

        new_builder.params.extend(group_builder.params)
        return new_builder

    def where_group(
        self, group_function: Callable[["QueryBuilder"], "QueryBuilder"]
    ) -> "QueryBuilder":
        """Add a grouped WHERE clause using a function"""
        return self._add_group_condition(group_function, is_or=False)

    def or_where_group(
        self, group_function: Callable[["QueryBuilder"], "QueryBuilder"]
    ) -> "QueryBuilder":
        """Add a grouped OR WHERE clause using a function"""
        return self._add_group_condition(group_function, is_or=True)

    def order_by(self, clause: str) -> "QueryBuilder":
        """Add ORDER BY clause"""
        new_builder = self._clone()
        new_builder.order_by_clause = f" ORDER BY {clause}"
        return new_builder

    def build(self) -> tuple[str, list[Any]]:
        """Build the final SQL query and parameters"""
        query_parts = [f"SELECT {self.select_fields} FROM {self.table_name}"]

        # Build WHERE clause
        where_parts = []

        if self.where_conditions:
            if len(self.where_conditions) == 1 and not self.or_where_conditions:
                where_parts.append(self.where_conditions[0])
            elif len(self.where_conditions) > 1 and not self.or_where_conditions:
                where_parts.append(" AND ".join(self.where_conditions))
            else:
                # AND conditions with OR conditions present
                if len(self.where_conditions) == 1:
                    where_parts.append(self.where_conditions[0])
                else:
                    where_parts.append(f"({' AND '.join(self.where_conditions)})")

        if self.or_where_conditions:
            if len(self.or_where_conditions) == 1:
                where_parts.append(self.or_where_conditions[0])
            else:
                where_parts.append(f"({' OR '.join(self.or_where_conditions)})")

        if where_parts:
            if len(where_parts) == 1:
                query_parts.append(f"WHERE {where_parts[0]}")
            else:
                query_parts.append(f"WHERE {' OR '.join(where_parts)}")

        if self.order_by_clause:
            query_parts.append(self.order_by_clause.strip())

        return " ".join(query_parts), self.params

    def to_sql(self) -> str:
        """Return only the SQL query string without parameters"""
        query, _ = self.build()
        return query

    def __str__(self) -> str:
        """String representation showing the built query"""
        query, params = self.build()
        return f"Query: {query}\nParams: {params}"

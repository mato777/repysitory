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
        self.order_by_parts: list[str] = []
        self.group_by_parts: list[str] = []
        self.having_conditions: list[str] = []
        self.select_alias_map: dict[str, str] = {}
        self.limit_count: int | None = None
        self.offset_count: int | None = None

    def _clone(self) -> "QueryBuilder":
        """Create a copy of the current QueryBuilder instance"""
        new_builder = QueryBuilder(self.table_name)
        new_builder.select_fields = self.select_fields
        new_builder.where_conditions = self.where_conditions.copy()
        new_builder.or_where_conditions = self.or_where_conditions.copy()
        new_builder.params = self.params.copy()
        new_builder.order_by_clause = self.order_by_clause
        new_builder.order_by_parts = self.order_by_parts.copy()
        new_builder.group_by_parts = self.group_by_parts.copy()
        new_builder.having_conditions = self.having_conditions.copy()
        new_builder.select_alias_map = self.select_alias_map.copy()
        new_builder.limit_count = self.limit_count
        new_builder.offset_count = self.offset_count
        return new_builder

    def _add_condition(
        self, field: str, value: Any, operator: str, is_or: bool = False
    ) -> "QueryBuilder":
        """Add a condition to either WHERE or OR WHERE clauses"""
        new_builder = self._clone()

        # Handle None values with IS NULL / IS NOT NULL
        if value is None:
            if operator == "=":
                condition = f"{field} IS NULL"
            elif operator in ("!=", "<>"):
                condition = f"{field} IS NOT NULL"
            else:
                # For other operators with None, treat as standard comparison
                # This might not make logical sense but maintains backward compatibility
                param_index = len(new_builder.params) + 1
                condition = f"{field} {operator} ${param_index}"
                new_builder.params.append(value)
        else:
            param_index = len(new_builder.params) + 1
            condition = f"{field} {operator} ${param_index}"
            new_builder.params.append(value)

        if is_or:
            new_builder.or_where_conditions.append(condition)
        else:
            new_builder.where_conditions.append(condition)

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
        import re

        def replace_param(match):
            param_num = int(match.group(1))
            if param_num <= total_group_params:
                return f"${param_offset + param_num}"
            return match.group(0)

        # Use regex to find and replace parameter placeholders
        # This avoids issues with overlapping replacements
        return re.sub(r"\$(\d+)", replace_param, condition)

    def select(self, *fields: str) -> "QueryBuilder":
        """Set the SELECT fields. Accepts one string or multiple field strings."""
        new_builder = self._clone()
        if not fields:
            new_builder.select_fields = "*"
            new_builder.select_alias_map = {}
        else:
            new_builder.select_fields = ", ".join(fields)
            # Build alias map for use in HAVING
            alias_map: dict[str, str] = {}
            import re

            alias_pattern = re.compile(
                r"^(.*?)\s+as\s+([A-Za-z_][A-Za-z0-9_]*)$", re.IGNORECASE
            )
            for raw in fields:
                part = raw.strip()
                m = alias_pattern.match(part)
                if m:
                    expr = m.group(1).strip()
                    alias = m.group(2)
                    alias_map[alias] = expr
            new_builder.select_alias_map = alias_map
        return new_builder

    def where(
        self,
        field_or_function: str | Callable[["QueryBuilder"], "QueryBuilder"],
        *args: Any,
    ) -> "QueryBuilder":
        """Add a WHERE condition or grouped WHERE clause.

        Supports both of the following call styles:
        - where(field, value) -> operator defaults to '='
        - where(field, operator, value) -> explicit operator in the second place

        Grouped conditions via function remain supported: where(lambda qb: ...)
        """
        if callable(field_or_function):
            return self.where_group(field_or_function)

        field = field_or_function
        # Determine argument style by length to support value=None in 3-arg form
        if len(args) == 2:
            operator, value = args
            return self._add_condition(field, value, operator, is_or=False)
        if len(args) == 1:
            value = args[0]
            return self._add_condition(field, value, "=", is_or=False)
        raise TypeError("where() expects (field, value) or (field, operator, value)")

    def or_where(
        self,
        field_or_function: str | Callable[["QueryBuilder"], "QueryBuilder"],
        *args: Any,
    ) -> "QueryBuilder":
        """Add an OR WHERE condition or grouped OR WHERE clause.

        Supports both of the following call styles:
        - or_where(field, value) -> operator defaults to '='
        - or_where(field, operator, value) -> explicit operator in the second place
        """
        if callable(field_or_function):
            return self.or_where_group(field_or_function)

        field = field_or_function
        if len(args) == 2:
            operator, value = args
            return self._add_condition(field, value, operator, is_or=True)
        if len(args) == 1:
            value = args[0]
            return self._add_condition(field, value, "=", is_or=True)
        raise TypeError("or_where() expects (field, value) or (field, operator, value)")

    def where_multiple(self, conditions: list[tuple[str, Any, str]]) -> "QueryBuilder":
        """Add multiple WHERE conditions.

        Expects tuples in the form: (field, operator, value)
        """
        new_builder = self._clone()
        for condition in conditions:
            field, operator, value = condition
            new_builder = new_builder._add_condition(
                field, value, operator, is_or=False
            )
        return new_builder

    def or_where_multiple(
        self, conditions: list[tuple[str, Any, str]]
    ) -> "QueryBuilder":
        """Add multiple OR WHERE conditions.

        Expects tuples in the form: (field, operator, value)
        """
        new_builder = self._clone()
        for condition in conditions:
            field, operator, value = condition
            new_builder = new_builder._add_condition(field, value, operator, is_or=True)
        return new_builder

    def where_any(
        self, conditions: tuple[str, Any, str] | list[tuple[str, Any, str]]
    ) -> "QueryBuilder":
        """Add WHERE condition(s) - accepts either a single tuple or a list of tuples.

        Expects tuple order: (field, operator, value)
        """
        if isinstance(conditions, tuple):
            field, operator, value = conditions
            return self.where(field, operator, value)
        return self.where_multiple(conditions)

    def or_where_any(
        self, conditions: tuple[str, Any, str] | list[tuple[str, Any, str]]
    ) -> "QueryBuilder":
        """Add OR WHERE condition(s) - accepts either a single tuple or a list of tuples.

        Expects tuple order: (field, operator, value)
        """
        if isinstance(conditions, tuple):
            field, operator, value = conditions
            return self.or_where(field, operator, value)
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

    def order_by(self, field: str) -> "QueryBuilder":
        """Add ORDER BY ascending for a field (default). Chain to add multiple fields."""
        new_builder = self._clone()
        new_builder.order_by_clause = ""
        new_builder.order_by_parts.append(f"{field}")
        return new_builder

    def order_by_asc(self, field: str) -> "QueryBuilder":
        """Add an ORDER BY ... ASC on the given field. Can be chained to add multiple fields."""
        new_builder = self._clone()
        new_builder.order_by_clause = ""
        new_builder.order_by_parts.append(f"{field}")
        return new_builder

    def order_by_desc(self, field: str) -> "QueryBuilder":
        """Add an ORDER BY ... DESC on the given field. Can be chained to add multiple fields."""
        new_builder = self._clone()
        new_builder.order_by_clause = ""
        new_builder.order_by_parts.append(f"{field} DESC")
        return new_builder

    def group_by(self, *fields: str) -> "QueryBuilder":
        """Add GROUP BY fields. Can be chained or passed multiple fields."""
        if not fields:
            return self
        new_builder = self._clone()
        for field in fields:
            if field:
                new_builder.group_by_parts.append(f"{field}")
        return new_builder

    def having(self, field: str, *args: Any) -> "QueryBuilder":
        """Add a HAVING condition.

        Supports both of the following call styles:
        - having(field, value) -> operator defaults to '='
        - having (field, operator, value) -> explicit operator in the second place
        """
        new_builder = self._clone()
        if len(args) == 2:
            operator, value = args
        elif len(args) == 1:
            operator, value = "=", args[0]
        else:
            raise TypeError(
                "having() expects (field, value) or (field, operator, value)"
            )

        # Resolve aliases from the SELECT list, if any
        resolved_field = new_builder.select_alias_map.get(field, field)
        param_index = len(new_builder.params) + 1
        condition = f"{resolved_field} {operator} ${param_index}"
        new_builder.having_conditions.append(condition)
        new_builder.params.append(value)
        return new_builder

    def limit(self, count: int) -> "QueryBuilder":
        """Set the LIMIT clause"""
        new_builder = self._clone()
        new_builder.limit_count = count
        return new_builder

    def offset(self, count: int) -> "QueryBuilder":
        """Set the OFFSET clause"""
        new_builder = self._clone()
        new_builder.offset_count = count
        return new_builder

    def paginate(self, page: int, per_page: int = 10) -> "QueryBuilder":
        """
        Set pagination parameters using a page-based interface

        Args:
            page: Page number (1-based)
            per_page: Number of records per page (default: 10)

        Returns:
            QueryBuilder with LIMIT and OFFSET set for the specified page
        """
        if page < 1:
            raise ValueError("Page number must be 1 or greater")
        if per_page < 1:
            raise ValueError("Per page count must be 1 or greater")

        offset = (page - 1) * per_page
        return self.limit(per_page).offset(offset)

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

        if self.group_by_parts:
            query_parts.append(f"GROUP BY {', '.join(self.group_by_parts)}")

        if self.having_conditions:
            if len(self.having_conditions) == 1:
                query_parts.append(f"HAVING {self.having_conditions[0]}")
            else:
                query_parts.append(f"HAVING {' AND '.join(self.having_conditions)}")

        if self.order_by_parts:
            query_parts.append(f"ORDER BY {', '.join(self.order_by_parts)}")
        elif self.order_by_clause:
            query_parts.append(self.order_by_clause.strip())

        if self.limit_count is not None:
            query_parts.append(f"LIMIT {self.limit_count}")

        if self.offset_count is not None:
            query_parts.append(f"OFFSET {self.offset_count}")

        return " ".join(query_parts), self.params

    def to_sql(self) -> str:
        """Return only the SQL query string without parameters"""
        query, _ = self.build()
        return query

    def __str__(self) -> str:
        """String representation showing the built query"""
        query, params = self.build()
        return f"Query: {query}\nParams: {params}"

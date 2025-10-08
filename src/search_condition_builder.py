from pydantic import BaseModel

from src.query_builder import QueryBuilder


class SearchConditionBuilder:
    """Composition class for building search conditions"""

    @staticmethod
    def apply_search_conditions(
        builder: QueryBuilder, search: BaseModel
    ) -> QueryBuilder:
        """Apply search conditions to the query builder"""
        search_dict = {k: v for k, v in search.model_dump().items() if v is not None}

        for field, value in search_dict.items():
            builder = builder.where(field, value)

        return builder

    @staticmethod
    def build_order_clause(sort_model: BaseModel | None) -> str:
        """Build ORDER BY clause from a sort model"""
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
    def apply_sort(builder: QueryBuilder, sort_model: BaseModel | None) -> QueryBuilder:
        """Apply sorting to the builder using order_by (ASC default) and order_by_desc."""
        if not sort_model:
            return builder

        sort_dict = {k: v for k, v in sort_model.model_dump().items() if v is not None}
        if not sort_dict:
            return builder

        for field, order in sort_dict.items():
            if str(order).upper() == "DESC":
                builder = builder.order_by_desc(field)
            else:
                builder = builder.order_by(field)

        return builder

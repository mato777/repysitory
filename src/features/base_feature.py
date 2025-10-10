"""Base feature interface for repository features"""

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

if TYPE_CHECKING:
    from src.query_builder import QueryBuilder


class RepositoryFeature:
    """
    Base class for repository features.

    Features can hook into repository lifecycle events to add functionality
    like timestamps, soft deletes, audit logs, etc.
    """

    def before_create(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Hook called before creating an entity.

        Args:
            data: Entity data dictionary

        Returns:
            Modified data dictionary
        """
        return data

    def before_update(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Hook called before updating an entity.

        Args:
            data: Update data dictionary

        Returns:
            Modified data dictionary
        """
        return data

    def augment_entity_class(self, entity_class: type[BaseModel]) -> type[BaseModel]:
        """
        Hook to augment the entity class with additional fields.

        Args:
            entity_class: Original entity class

        Returns:
            Augmented entity class (can return the same if no augmentation needed)
        """
        return entity_class

    def apply_query_filters(self, builder: "QueryBuilder") -> "QueryBuilder":
        """
        Hook to apply automatic filters to queries (e.g., WHERE deleted_at IS NULL).

        Args:
            builder: Query builder instance

        Returns:
            Modified query builder
        """
        return builder

    def should_intercept_delete(self) -> bool:
        """
        Whether this feature should intercept delete operations.

        Returns:
            True if delete should be intercepted (e.g., for soft delete)
        """
        return False

    def handle_delete(self, entity_id: Any) -> dict[str, Any] | None:
        """
        Handle a delete operation (called if should_intercept_delete returns True).

        Args:
            entity_id: ID of entity to delete

        Returns:
            Update data to apply instead of delete, or None to proceed with delete
        """
        return None

"""Soft Delete feature for automatic soft delete management"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, create_model

from src.features.base_feature import RepositoryFeature


class SoftDeleteFeature(RepositoryFeature):
    """
    Feature that adds soft delete functionality to repositories.

    Soft delete means records are marked as deleted (deleted_at timestamp)
    instead of being physically removed from the database.

    This feature automatically:
    - Adds a 'deleted_at' field to entities
    - Intercepts delete() calls to set deleted_at instead of hard deleting
    - Filters out soft-deleted records in queries by default

    Usage:
        config = RepositoryConfig(features=[SoftDeleteFeature()])
        repo = Repository(..., config=config)

        # Soft delete (sets deleted_at)
        await repo.delete(id)
        await repo.where("status", "inactive").delete()

        # Force delete (actually removes from a database)
        await repo.force_delete(id)

        # Restore soft-deleted record
        await repo.restore(id)

        # Query with soft-deleted records
        await repo.with_trashed().get() # Include soft-deleted
        await repo.only_trashed().get() # Only soft-deleted
        await repo.get()  # Default: exclude soft-deleted
    """

    def before_create(self, data: dict[str, Any]) -> dict[str, Any]:
        """Set deleted_at to None on creation (entity is not deleted)"""
        data["deleted_at"] = None
        return data

    def augment_entity_class(self, entity_class: type[BaseModel]) -> type[BaseModel]:
        """Add the deleted_at field to the entity class"""
        # Check if deleted_at field already exists
        if "deleted_at" in entity_class.model_fields:
            return entity_class

        # Create a new model class with just the soft delete field
        return create_model(
            f"{entity_class.__name__}WithSoftDelete",
            __base__=entity_class,
            deleted_at=(datetime | None, None),
        )

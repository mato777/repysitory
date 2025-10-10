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
        # Get the original model fields
        original_fields = entity_class.model_fields

        # Add a soft delete field
        soft_delete_field = {
            "deleted_at": (datetime | None, None),
        }

        # Combine original fields with soft delete field
        all_fields = {**original_fields, **soft_delete_field}

        # Create field definitions for create_model
        field_definitions = {}
        for name, field_info in all_fields.items():
            if hasattr(field_info, "annotation") and hasattr(field_info, "default"):
                field_definitions[name] = (field_info.annotation, field_info.default)
            else:
                # For soft delete field, use the tuple directly
                field_definitions[name] = field_info

        # Create a new model class
        return create_model(
            f"{entity_class.__name__}WithSoftDelete",
            __base__=entity_class,
            **field_definitions,
        )

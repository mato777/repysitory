"""Timestamp feature for automatic timestamp management"""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, create_model

from src.features.base_feature import RepositoryFeature


class TimestampFeature(RepositoryFeature):
    """
    Feature that adds automatic timestamp management to entities.

    Adds `created_at` and `updated_at` fields to entities and automatically
    populates them during create and update operations.
    """

    @staticmethod
    def _get_current_timestamp() -> datetime:
        """Get current UTC timestamp as a datetime object"""
        return datetime.now(UTC)

    def before_create(self, data: dict[str, Any]) -> dict[str, Any]:
        """Inject created_at and updated_at timestamps"""
        timestamp = self._get_current_timestamp()
        data["created_at"] = timestamp
        data["updated_at"] = timestamp
        return data

    def before_update(self, data: dict[str, Any]) -> dict[str, Any]:
        """Inject updated_at timestamp"""
        data["updated_at"] = self._get_current_timestamp()
        return data

    def augment_entity_class(self, entity_class: type[BaseModel]) -> type[BaseModel]:
        """Add timestamp fields to the entity class"""
        # Check if timestamp fields already exist
        if (
            "created_at" in entity_class.model_fields
            and "updated_at" in entity_class.model_fields
        ):
            return entity_class

        # Create a new model class with just the timestamp fields
        return create_model(
            f"{entity_class.__name__}WithTimestamps",
            __base__=entity_class,
            created_at=(datetime, None),
            updated_at=(datetime, None),
        )

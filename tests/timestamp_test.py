"""
Tests for automatic timestamp functionality in Repository
"""

from datetime import datetime
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel

from src.entities import BaseEntity
from src.repository import Repository


class TimestampedEntity(BaseEntity):
    """Test entity for timestamp functionality"""

    name: str
    description: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class TimestampedEntitySearch(BaseModel):
    """Search model for timestamped entity"""

    id: UUID | None = None
    name: str | None = None
    description: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class TimestampedEntityUpdate(BaseModel):
    """Update model for timestamped entity"""

    name: str | None = None
    description: str | None = None


class NonTimestampedEntity(BaseEntity):
    """Test entity without timestamps"""

    name: str
    description: str | None = None


class NonTimestampedEntitySearch(BaseModel):
    """Search model for non-timestamped entity"""

    id: UUID | None = None
    name: str | None = None
    description: str | None = None


class NonTimestampedEntityUpdate(BaseModel):
    """Update model for non-timestamped entity"""

    name: str | None = None
    description: str | None = None


class TestTimestampFunctionality:
    """Test timestamp functionality in Repository"""

    @pytest.fixture
    def timestamped_repo(self):
        """Repository with timestamps enabled"""
        return Repository(
            entity_schema_class=TimestampedEntity,
            entity_domain_class=TimestampedEntity,
            update_class=TimestampedEntityUpdate,
            table_name="timestamped_entities",
        )

    @pytest.fixture
    def non_timestamped_repo(self):
        """Repository without timestamps"""
        return Repository(
            entity_schema_class=NonTimestampedEntity,
            entity_domain_class=NonTimestampedEntity,
            update_class=NonTimestampedEntityUpdate,
            table_name="non_timestamped_entities",
        )

    def test_timestamp_injection_on_create(self, timestamped_repo):
        """Test that timestamps are injected when creating entities"""
        entity = TimestampedEntity(name="Test Entity", description="Test Description")

        # Test timestamp injection using automatic fields based on schema
        fields = entity.model_dump()
        injected_fields = timestamped_repo._apply_automatic_fields(
            fields, is_create=True
        )

        assert "created_at" in injected_fields
        assert "updated_at" in injected_fields
        assert injected_fields["created_at"] == injected_fields["updated_at"]

        # Verify timestamp format (datetime object)
        timestamp = injected_fields["created_at"]
        assert isinstance(timestamp, datetime)
        assert timestamp.tzinfo is not None  # Should have timezone info

    def test_timestamp_injection_on_update(self, timestamped_repo):
        """Test that only updated_at is injected when updating entities"""
        update_data = {"name": "Updated Name"}

        injected_data = timestamped_repo._apply_automatic_fields(
            update_data, is_create=False
        )

        assert "updated_at" in injected_data
        assert "created_at" not in injected_data

        # Verify timestamp format (datetime object)
        timestamp = injected_data["updated_at"]
        assert isinstance(timestamp, datetime)
        assert timestamp.tzinfo is not None  # Should have timezone info

    def test_no_timestamp_injection_when_disabled(self, non_timestamped_repo):
        """Test that timestamps are not injected when timestamps=False"""
        entity = NonTimestampedEntity(
            name="Test Entity", description="Test Description"
        )

        fields = entity.model_dump()
        injected_fields = non_timestamped_repo._apply_automatic_fields(
            fields, is_create=True
        )

        assert "created_at" not in injected_fields
        assert "updated_at" not in injected_fields
        assert injected_fields == fields

    def test_timestamp_injection_preserves_existing_data(self, timestamped_repo):
        """Test that timestamp injection doesn't modify existing data"""
        original_data = {
            "id": str(uuid4()),
            "name": "Test Entity",
            "description": "Test Description",
        }

        injected_data = timestamped_repo._apply_automatic_fields(
            original_data, is_create=True
        )

        # Original data should be preserved
        assert injected_data["id"] == original_data["id"]
        assert injected_data["name"] == original_data["name"]
        assert injected_data["description"] == original_data["description"]

        # Timestamps should be added
        assert "created_at" in injected_data
        assert "updated_at" in injected_data

    def test_multiple_timestamp_calls_produce_different_timestamps(
        self, timestamped_repo
    ):
        """Test that multiple calls produce different timestamps"""
        import time

        data1 = {"name": "Entity 1"}
        data2 = {"name": "Entity 2"}

        injected1 = timestamped_repo._apply_automatic_fields(data1, is_create=True)
        time.sleep(0.001)  # Small delay to ensure different timestamps
        injected2 = timestamped_repo._apply_automatic_fields(data2, is_create=True)

        assert injected1["created_at"] != injected2["created_at"]
        assert injected1["updated_at"] != injected2["updated_at"]

    def test_timestamp_format_is_datetime_object(self, timestamped_repo):
        """Test that timestamps are datetime objects"""
        data = {"name": "Test Entity"}
        injected_data = timestamped_repo._apply_automatic_fields(data, is_create=True)

        timestamp = injected_data["created_at"]

        # Should be a datetime object
        assert isinstance(timestamp, datetime)
        assert timestamp.tzinfo is not None  # Should have timezone info

    def test_timestamp_injection_with_empty_data(self, timestamped_repo):
        """Test timestamp injection with empty data dictionary"""
        empty_data = {}

        injected_data = timestamped_repo._apply_automatic_fields(
            empty_data, is_create=True
        )

        assert len(injected_data) == 2
        assert "created_at" in injected_data
        assert "updated_at" in injected_data

    def test_timestamp_injection_with_none_values(self, timestamped_repo):
        """Test timestamp injection with None values"""
        data_with_none = {
            "name": "Test Entity",
            "description": None,
            "optional_field": None,
        }

        injected_data = timestamped_repo._apply_automatic_fields(
            data_with_none, is_create=True
        )

        # Original data should be preserved including None values
        assert injected_data["name"] == "Test Entity"
        assert injected_data["description"] is None
        assert injected_data["optional_field"] is None

        # Timestamps should be added
        assert "created_at" in injected_data
        assert "updated_at" in injected_data

    def test_repository_constructor_with_timestamp_fields(self):
        """Repository detects timestamp fields from schema"""
        repo = Repository(
            entity_schema_class=TimestampedEntity,
            entity_domain_class=TimestampedEntity,
            update_class=TimestampedEntityUpdate,
            table_name="test_table",
        )

        assert repo._has_created_at is True
        assert repo._has_updated_at is True
        assert repo.entity_schema_class == TimestampedEntity
        assert repo.entity_domain_class == TimestampedEntity
        assert repo.update_class == TimestampedEntityUpdate
        assert repo.table_name == "test_table"

    def test_repository_constructor_without_timestamp_fields(self):
        """Repository detects absence of timestamp fields from schema"""
        repo = Repository(
            entity_schema_class=NonTimestampedEntity,
            entity_domain_class=NonTimestampedEntity,
            update_class=NonTimestampedEntityUpdate,
            table_name="test_table",
        )

        assert repo._has_created_at is False
        assert repo._has_updated_at is False

    def test_repository_constructor_flags_default_from_schema(self):
        """Repository flags default to schema field detection"""
        repo = Repository(
            entity_schema_class=NonTimestampedEntity,
            entity_domain_class=NonTimestampedEntity,
            update_class=NonTimestampedEntityUpdate,
            table_name="test_table",
        )

        assert repo._has_created_at is False
        assert repo._has_updated_at is False

    def test_clone_with_query_builder_preserves_timestamps_setting(
        self, timestamped_repo
    ):
        """Test that cloning preserves the timestamps setting"""
        from src.query_builder import QueryBuilder

        query_builder = QueryBuilder("test_table")
        cloned_repo = timestamped_repo._clone_with_query_builder(query_builder)

        assert cloned_repo._has_created_at is True
        assert cloned_repo._has_updated_at is True
        assert cloned_repo.entity_schema_class == timestamped_repo.entity_schema_class
        assert cloned_repo.update_class == timestamped_repo.update_class
        assert cloned_repo.table_name == timestamped_repo.table_name
        assert cloned_repo.config.db_schema == timestamped_repo.config.db_schema

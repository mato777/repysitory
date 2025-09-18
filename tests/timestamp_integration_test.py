"""
Integration tests for timestamp functionality with database operations
"""

from datetime import datetime
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from pydantic import BaseModel

from src.db_context import transactional
from src.entities import BaseEntity
from src.repository import Repository


class TimestampedPost(BaseEntity):
    """Post entity with timestamps"""

    title: str
    content: str
    published: bool = False


class TimestampedPostSearch(BaseModel):
    """Search model for timestamped post"""

    id: UUID | None = None
    title: str | None = None
    content: str | None = None
    published: bool | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class TimestampedPostUpdate(BaseModel):
    """Update model for timestamped post"""

    title: str | None = None
    content: str | None = None
    published: bool | None = None


class TestTimestampIntegration:
    """Integration tests for timestamp functionality with database"""

    @pytest_asyncio.fixture
    async def timestamped_post_repo(self, test_db_pool):
        """Repository with timestamps enabled for posts"""
        async with test_db_pool.acquire() as conn:
            # Create table with timestamp columns
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS timestamped_posts (
                    id UUID PRIMARY KEY,
                    title VARCHAR(255) NOT NULL,
                    content TEXT,
                    published BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP WITH TIME ZONE,
                    updated_at TIMESTAMP WITH TIME ZONE
                )
            """)

        return Repository(
            entity_class=TimestampedPost,
            search_class=TimestampedPostSearch,
            update_class=TimestampedPostUpdate,
            table_name="timestamped_posts",
            timestamps=True,
        )

    @pytest_asyncio.fixture
    async def non_timestamped_post_repo(self, test_db_pool):
        """Repository without timestamps for posts"""
        async with test_db_pool.acquire() as conn:
            # Create table without timestamp columns
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS non_timestamped_posts (
                    id UUID PRIMARY KEY,
                    title VARCHAR(255) NOT NULL,
                    content TEXT,
                    published BOOLEAN DEFAULT FALSE
                )
            """)

        return Repository(
            entity_class=TimestampedPost,
            search_class=TimestampedPostSearch,
            update_class=TimestampedPostUpdate,
            table_name="non_timestamped_posts",
            timestamps=False,
        )

    @pytest.mark.asyncio
    @transactional("test")
    async def test_create_with_timestamps(self, timestamped_post_repo):
        """Test creating an entity with automatic timestamps"""
        post = TimestampedPost(
            id=uuid4(), title="Test Post", content="This is a test post", published=True
        )

        created_post = await timestamped_post_repo.create(post)

        # Verify timestamps were added
        assert hasattr(created_post, "created_at")
        assert hasattr(created_post, "updated_at")
        assert created_post.created_at == created_post.updated_at

        # Verify timestamp format
        timestamp = created_post.created_at
        assert isinstance(timestamp, datetime)
        assert timestamp.tzinfo is not None  # Should have timezone info

        # Verify other fields are preserved
        assert created_post.title == "Test Post"
        assert created_post.content == "This is a test post"
        assert created_post.published is True

    @pytest.mark.asyncio
    @transactional("test")
    async def test_create_without_timestamps(self, non_timestamped_post_repo):
        """Test creating an entity without timestamps"""
        post = TimestampedPost(
            id=uuid4(), title="Test Post", content="This is a test post", published=True
        )

        created_post = await non_timestamped_post_repo.create(post)

        # Verify timestamps were NOT added
        assert not hasattr(created_post, "created_at")
        assert not hasattr(created_post, "updated_at")

        # Verify other fields are preserved
        assert created_post.title == "Test Post"
        assert created_post.content == "This is a test post"
        assert created_post.published is True

    @pytest.mark.asyncio
    @transactional("test")
    async def test_create_many_with_timestamps(self, timestamped_post_repo):
        """Test creating multiple entities with timestamps"""
        posts = [
            TimestampedPost(id=uuid4(), title=f"Post {i}", content=f"Content {i}")
            for i in range(3)
        ]

        created_posts = await timestamped_post_repo.create_many(posts)

        assert len(created_posts) == 3

        for post in created_posts:
            assert hasattr(post, "created_at")
            assert hasattr(post, "updated_at")
            assert post.created_at == post.updated_at

    @pytest.mark.asyncio
    @transactional("test")
    async def test_update_with_timestamps(self, timestamped_post_repo):
        """Test updating an entity with automatic timestamp update"""
        # Create initial post
        post = TimestampedPost(
            id=uuid4(),
            title="Original Title",
            content="Original content",
            published=False,
        )
        created_post = await timestamped_post_repo.create(post)
        original_created_at = created_post.created_at
        original_updated_at = created_post.updated_at

        # Wait a small amount to ensure timestamp difference
        import time

        time.sleep(0.001)

        # Update the post
        update_data = TimestampedPostUpdate(title="Updated Title", published=True)
        updated_post = await timestamped_post_repo.update(created_post.id, update_data)

        # Verify timestamps
        assert updated_post.created_at == original_created_at  # Should not change
        assert updated_post.updated_at != original_updated_at  # Should be updated
        assert updated_post.updated_at > original_updated_at  # Should be newer

        # Verify updated fields
        assert updated_post.title == "Updated Title"
        assert updated_post.published is True
        assert updated_post.content == "Original content"  # Should remain unchanged

    @pytest.mark.asyncio
    @transactional("test")
    async def test_find_by_id_with_timestamps(self, timestamped_post_repo):
        """Test finding entity by ID includes timestamps"""
        post = TimestampedPost(
            id=uuid4(),
            title="Find Test Post",
            content="This post will be found",
            published=True,
        )
        created_post = await timestamped_post_repo.create(post)

        found_post = await timestamped_post_repo.find_by_id(created_post.id)

        assert found_post is not None
        assert found_post.id == created_post.id
        assert found_post.title == "Find Test Post"
        assert hasattr(found_post, "created_at")
        assert hasattr(found_post, "updated_at")

    @pytest.mark.asyncio
    @transactional("test")
    async def test_find_many_by_with_timestamps(self, timestamped_post_repo):
        """Test finding multiple entities includes timestamps"""
        # Create multiple posts
        posts = [
            TimestampedPost(
                id=uuid4(), title=f"Search Post {i}", content=f"Content {i}"
            )
            for i in range(3)
        ]
        await timestamped_post_repo.create_many(posts)

        # Search for posts
        search_criteria = TimestampedPostSearch(title="Search Post 1")
        found_posts = await timestamped_post_repo.find_many_by(search_criteria)

        assert len(found_posts) == 1
        found_post = found_posts[0]
        assert found_post.title == "Search Post 1"
        assert hasattr(found_post, "created_at")
        assert hasattr(found_post, "updated_at")

    @pytest.mark.asyncio
    @transactional("test")
    async def test_timestamp_consistency_across_operations(self, timestamped_post_repo):
        """Test that timestamps remain consistent across operations"""
        post = TimestampedPost(
            id=uuid4(),
            title="Consistency Test",
            content="Testing timestamp consistency",
        )

        # Create
        created_post = await timestamped_post_repo.create(post)
        created_at = created_post.created_at
        updated_at = created_post.updated_at

        # Find by ID
        found_post = await timestamped_post_repo.find_by_id(created_post.id)
        assert found_post.created_at == created_at
        assert found_post.updated_at == updated_at

        # Update
        import time

        time.sleep(0.001)
        update_data = TimestampedPostUpdate(title="Updated Consistency Test")
        updated_post = await timestamped_post_repo.update(created_post.id, update_data)

        assert updated_post.created_at == created_at  # Should not change
        assert updated_post.updated_at != updated_at  # Should be different
        assert updated_post.updated_at > updated_at  # Should be newer

    @pytest.mark.asyncio
    @transactional("test")
    async def test_timestamp_search_functionality(self, timestamped_post_repo):
        """Test searching by timestamp fields"""
        post = TimestampedPost(
            id=uuid4(),
            title="Timestamp Search Test",
            content="Testing timestamp search",
        )
        created_post = await timestamped_post_repo.create(post)

        # Search by created_at
        search_by_created = TimestampedPostSearch(created_at=created_post.created_at)
        found_posts = await timestamped_post_repo.find_many_by(search_by_created)
        assert len(found_posts) == 1
        assert found_posts[0].id == created_post.id

        # Search by updated_at
        search_by_updated = TimestampedPostSearch(updated_at=created_post.updated_at)
        found_posts = await timestamped_post_repo.find_many_by(search_by_updated)
        assert len(found_posts) == 1
        assert found_posts[0].id == created_post.id

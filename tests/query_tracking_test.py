"""Tests for query tracking functionality"""

from uuid import uuid4

import pytest

from src.db_context import DatabaseManager
from src.repository import Repository
from tests.post_entities import Post, PostUpdate


@pytest.mark.asyncio
async def test_basic_query_tracking():
    """Test basic query tracking functionality"""
    post_repo = Repository(
        entity_schema_class=Post,
        entity_domain_class=Post,
        update_class=PostUpdate,
        table_name="posts",
    )
    post_id = uuid4()

    async with (
        DatabaseManager.transaction("test_db"),
        DatabaseManager.track_queries() as tracker,
    ):
        # Create and fetch a post
        new_post = Post(id=post_id, title="Test Post", content="Test Content")
        await post_repo.create(new_post)
        await post_repo.find_by_id(post_id)

        # Verify queries were tracked
        queries = tracker.get_queries()
        assert len(queries) == 2

        # Verify first query is INSERT
        assert "INSERT INTO posts" in queries[0].query
        assert post_id in queries[0].params

        # Verify second query is SELECT
        assert "SELECT" in queries[1].query
        assert str(post_id) in queries[1].params


@pytest.mark.asyncio
async def test_query_tracking_with_fluent_interface():
    """Test query tracking with fluent query builder"""
    post_repo = Repository(
        entity_schema_class=Post,
        entity_domain_class=Post,
        update_class=PostUpdate,
        table_name="posts",
    )

    async with (
        DatabaseManager.transaction("test_db"),
        DatabaseManager.track_queries() as tracker,
    ):
        # Execute a complex query
        await (
            post_repo.where("title", "LIKE", "Test%")
            .order_by_desc("id")
            .limit(10)
            .get()
        )

        queries = tracker.get_queries()
        assert len(queries) == 1

        query = queries[0].query
        assert "WHERE" in query
        assert "LIKE" in query
        assert "ORDER BY" in query
        assert "LIMIT" in query


@pytest.mark.asyncio
async def test_query_tracking_count():
    """Test query tracking with count operations"""
    post_repo = Repository(
        entity_schema_class=Post,
        entity_domain_class=Post,
        update_class=PostUpdate,
        table_name="posts",
    )

    async with (
        DatabaseManager.transaction("test_db"),
        DatabaseManager.track_queries() as tracker,
    ):
        # Create posts
        posts = [
            Post(id=uuid4(), title=f"Post {i}", content=f"Content {i}")
            for i in range(3)
        ]
        await post_repo.create_many(posts)

        # Count posts
        count = await post_repo.where("title", "LIKE", "Post%").count()

        queries = tracker.get_queries()

        # Should have INSERT and COUNT queries
        assert len(queries) == 2
        assert "INSERT" in queries[0].query
        assert "COUNT(*)" in queries[1].query
        assert count == 3


@pytest.mark.asyncio
async def test_tracker_clear():
    """Test clearing tracked queries"""
    post_repo = Repository(
        entity_schema_class=Post,
        entity_domain_class=Post,
        update_class=PostUpdate,
        table_name="posts",
    )

    async with (
        DatabaseManager.transaction("test_db"),
        DatabaseManager.track_queries() as tracker,
    ):
        # Execute some queries
        await post_repo.limit(5).get()
        assert tracker.count() > 0

        # Clear tracker
        tracker.clear()
        assert tracker.count() == 0

        # Execute more queries
        await post_repo.count()
        assert tracker.count() == 1


@pytest.mark.asyncio
async def test_tracker_to_dict():
    """Test converting tracker to dictionary"""
    post_repo = Repository(
        entity_schema_class=Post,
        entity_domain_class=Post,
        update_class=PostUpdate,
        table_name="posts",
    )

    async with (
        DatabaseManager.transaction("test_db"),
        DatabaseManager.track_queries() as tracker,
    ):
        await post_repo.limit(1).get()

        queries_dict = tracker.to_dict()
        assert isinstance(queries_dict, list)
        assert len(queries_dict) > 0

        first_query = queries_dict[0]
        assert "query" in first_query
        assert "params" in first_query
        assert "timestamp" in first_query
        assert isinstance(first_query["timestamp"], str)


@pytest.mark.asyncio
async def test_query_tracking_with_transaction_parameter():
    """Test query tracking enabled via transaction parameter"""
    post_repo = Repository(
        entity_schema_class=Post,
        entity_domain_class=Post,
        update_class=PostUpdate,
        table_name="posts",
    )
    post_id = uuid4()

    async with DatabaseManager.transaction("test_db", track_queries=True):
        new_post = Post(id=post_id, title="Test", content="Content")
        await post_repo.create(new_post)

        tracker = Repository.get_query_tracker()
        assert tracker is not None
        assert tracker.is_enabled()
        assert tracker.count() > 0


@pytest.mark.asyncio
async def test_no_tracking_without_context():
    """Test that queries are not tracked without context"""
    post_repo = Repository(
        entity_schema_class=Post,
        entity_domain_class=Post,
        update_class=PostUpdate,
        table_name="posts",
    )

    async with DatabaseManager.transaction("test_db"):
        # No tracking context
        await post_repo.limit(1).get()

        tracker = Repository.get_query_tracker()
        assert tracker is None


@pytest.mark.asyncio
async def test_nested_tracking_contexts():
    """Test nested tracking contexts share the same tracker"""
    post_repo = Repository(
        entity_schema_class=Post,
        entity_domain_class=Post,
        update_class=PostUpdate,
        table_name="posts",
    )

    async with (
        DatabaseManager.transaction("test_db"),
        DatabaseManager.track_queries() as outer_tracker,
        DatabaseManager.track_queries() as inner_tracker,
    ):
        await post_repo.limit(1).get()
        first_count = outer_tracker.count()

        # Nested context
        async with DatabaseManager.track_queries() as inner_tracker:
            await post_repo.count()

            # Should be the same tracker
            assert inner_tracker is outer_tracker
            assert inner_tracker.count() == first_count + 1

        # Continue using outer tracker
        await post_repo.where("title", "LIKE", "Test%").get()
        assert outer_tracker.count() == first_count + 2


@pytest.mark.asyncio
async def test_tracking_update_operations():
    """Test tracking UPDATE queries"""
    post_repo = Repository(
        entity_schema_class=Post,
        entity_domain_class=Post,
        update_class=PostUpdate,
        table_name="posts",
    )
    post_id = uuid4()

    async with DatabaseManager.transaction("test_db"):
        # Create post first
        new_post = Post(id=post_id, title="Original", content="Content")
        await post_repo.create(new_post)

        async with DatabaseManager.track_queries() as tracker:
            # Update post
            update_data = PostUpdate(title="Updated")
            await post_repo.update(post_id, update_data)

            queries = tracker.get_queries()

            # Should have UPDATE and SELECT queries
            assert len(queries) == 2
            assert "UPDATE posts" in queries[0].query
            assert "SELECT" in queries[1].query


@pytest.mark.asyncio
async def test_tracking_delete_operations():
    """Test tracking DELETE queries"""
    post_repo = Repository(
        entity_schema_class=Post,
        entity_domain_class=Post,
        update_class=PostUpdate,
        table_name="posts",
    )
    post_id = uuid4()

    async with DatabaseManager.transaction("test_db"):
        # Create post first
        new_post = Post(id=post_id, title="To Delete", content="Content")
        await post_repo.create(new_post)

        async with DatabaseManager.track_queries() as tracker:
            # Delete post
            await post_repo.delete(post_id)

            queries = tracker.get_queries()
            assert len(queries) == 1
            assert "DELETE FROM posts" in queries[0].query


@pytest.mark.asyncio
async def test_tracking_bulk_operations():
    """Test tracking bulk operations"""
    post_repo = Repository(
        entity_schema_class=Post,
        entity_domain_class=Post,
        update_class=PostUpdate,
        table_name="posts",
    )

    async with (
        DatabaseManager.transaction("test_db"),
        DatabaseManager.track_queries() as tracker,
    ):
        # Create multiple posts
        posts = [
            Post(id=uuid4(), title=f"Bulk Post {i}", content=f"Content {i}")
            for i in range(5)
        ]
        await post_repo.create_many(posts)

        queries = tracker.get_queries()
        assert len(queries) == 1

        # Should be a single INSERT with multiple value sets
        assert "INSERT INTO posts" in queries[0].query
        # Post has 6 fields: id, title, content, published, category, author_id
        assert len(queries[0].params) == len(posts) * 6


@pytest.mark.asyncio
async def test_tracking_where_in_queries():
    """Test tracking WHERE IN queries"""
    post_repo = Repository(
        entity_schema_class=Post,
        entity_domain_class=Post,
        update_class=PostUpdate,
        table_name="posts",
    )

    async with (
        DatabaseManager.transaction("test_db"),
        DatabaseManager.track_queries() as tracker,
    ):
        # Query with WHERE IN
        test_ids = [str(uuid4()) for _ in range(3)]
        await post_repo.where_in("id", test_ids).get()

        queries = tracker.get_queries()
        assert len(queries) == 1
        assert "WHERE" in queries[0].query
        assert "IN" in queries[0].query


@pytest.mark.asyncio
async def test_query_tracker_enable_disable():
    """Test enabling and disabling query tracker"""
    post_repo = Repository(
        entity_schema_class=Post,
        entity_domain_class=Post,
        update_class=PostUpdate,
        table_name="posts",
    )

    async with (
        DatabaseManager.transaction("test_db"),
        DatabaseManager.track_queries() as tracker,
    ):
        # Initially enabled
        assert tracker.is_enabled()

        # Execute query
        await post_repo.limit(1).get()
        assert tracker.count() == 1

        # Disable tracking
        tracker.disable()
        assert not tracker.is_enabled()

        # Execute another query - should not be tracked
        await post_repo.count()
        assert tracker.count() == 1  # Still 1

        # Re-enable tracking
        tracker.enable()
        assert tracker.is_enabled()

        # Execute query - should be tracked
        await post_repo.limit(2).get()
        assert tracker.count() == 2


@pytest.mark.asyncio
async def test_query_log_timestamp():
    """Test that query logs include timestamps"""
    post_repo = Repository(
        entity_schema_class=Post,
        entity_domain_class=Post,
        update_class=PostUpdate,
        table_name="posts",
    )

    async with (
        DatabaseManager.transaction("test_db"),
        DatabaseManager.track_queries() as tracker,
    ):
        await post_repo.limit(1).get()

        queries = tracker.get_queries()
        assert len(queries) == 1

        query_log = queries[0]
        assert query_log.timestamp is not None
        assert query_log.timestamp.tzinfo is not None  # Should be timezone-aware


@pytest.mark.asyncio
async def test_tracking_with_select_fields():
    """Test tracking queries with custom SELECT fields"""
    post_repo = Repository(
        entity_schema_class=Post,
        entity_domain_class=Post,
        update_class=PostUpdate,
        table_name="posts",
    )

    async with (
        DatabaseManager.transaction("test_db"),
        DatabaseManager.track_queries() as tracker,
    ):
        # Query with custom select fields
        await post_repo.select("id", "title").limit(5).get()

        queries = tracker.get_queries()
        assert len(queries) == 1
        assert "SELECT id, title FROM" in queries[0].query


@pytest.mark.asyncio
async def test_tracking_group_by_queries():
    """Test tracking GROUP BY queries"""
    post_repo = Repository(
        entity_schema_class=Post,
        entity_domain_class=Post,
        update_class=PostUpdate,
        table_name="posts",
    )

    async with (
        DatabaseManager.transaction("test_db"),
        DatabaseManager.track_queries() as tracker,
    ):
        # Query with GROUP BY
        await post_repo.select("title", "COUNT(*) as count").group_by("title").get()

        queries = tracker.get_queries()
        assert len(queries) == 1
        assert "GROUP BY" in queries[0].query


@pytest.mark.asyncio
async def test_multiple_repositories_tracking():
    """Test tracking queries from multiple repositories"""
    post_repo = Repository(
        entity_schema_class=Post,
        entity_domain_class=Post,
        update_class=PostUpdate,
        table_name="posts",
    )

    async with (
        DatabaseManager.transaction("test_db"),
        DatabaseManager.track_queries() as tracker,
    ):
        # Operations on first repo
        await post_repo.limit(2).get()
        first_count = tracker.count()

        # Operations on another instance
        another_post_repo = Repository(
            entity_schema_class=Post,
            entity_domain_class=Post,
            update_class=PostUpdate,
            table_name="posts",
        )
        await another_post_repo.count()

        # All queries should be tracked in the same tracker
        assert tracker.count() == first_count + 1

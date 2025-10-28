"""Tests for @transactional decorator with query tracking"""

from uuid import uuid4

import pytest

from src.db_context import transactional
from src.repository import Repository
from tests.post_entities import Post, PostUpdate


@pytest.mark.asyncio
async def test_transactional_with_query_logs_enabled():
    """Test @transactional decorator with query_logs=True"""
    post_repo = Repository(
        entity_schema_class=Post,
        entity_domain_class=Post,
        update_class=PostUpdate,
        table_name="posts",
    )
    post_id = uuid4()

    @transactional(db_name="test_db", query_logs=True)
    async def create_and_fetch_post():
        new_post = Post(id=post_id, title="Test Post", content="Test Content")
        await post_repo.create(new_post)
        found_post = await post_repo.find_by_id(post_id)

        # Get tracker inside the decorated function
        tracker = Repository.get_query_tracker()
        assert tracker is not None
        assert tracker.is_enabled()
        assert tracker.count() == 2  # INSERT and SELECT

        return found_post, tracker.get_queries()

    result, queries = await create_and_fetch_post()
    assert result is not None
    assert len(queries) == 2
    assert "INSERT INTO posts" in queries[0].query
    assert "SELECT" in queries[1].query


@pytest.mark.asyncio
async def test_transactional_without_query_logs():
    """Test @transactional decorator with query_logs=False (default)"""
    post_repo = Repository(
        entity_schema_class=Post,
        entity_domain_class=Post,
        update_class=PostUpdate,
        table_name="posts",
    )
    post_id = uuid4()

    @transactional(db_name="test_db")
    async def create_post():
        new_post = Post(id=post_id, title="Test Post", content="Test Content")
        await post_repo.create(new_post)

        # Tracker should not be available
        tracker = Repository.get_query_tracker()
        assert tracker is None

    await create_post()


@pytest.mark.asyncio
async def test_transactional_query_logs_with_return_value():
    """Test that decorated function can return values with query tracking"""
    post_repo = Repository(
        entity_schema_class=Post,
        entity_domain_class=Post,
        update_class=PostUpdate,
        table_name="posts",
    )

    @transactional(db_name="test_db", query_logs=True)
    async def get_post_count():
        posts = [
            Post(id=uuid4(), title=f"Post {i}", content=f"Content {i}")
            for i in range(3)
        ]
        await post_repo.create_many(posts)

        count = await post_repo.count()
        tracker = Repository.get_query_tracker()

        return count, tracker.count() if tracker else 0

    post_count, query_count = await get_post_count()
    assert post_count == 3
    assert query_count == 2  # INSERT and COUNT


@pytest.mark.asyncio
async def test_transactional_query_logs_with_complex_operations():
    """Test @transactional with query_logs on complex operations"""
    post_repo = Repository(
        entity_schema_class=Post,
        entity_domain_class=Post,
        update_class=PostUpdate,
        table_name="posts",
    )

    @transactional(db_name="test_db", query_logs=True)
    async def complex_operation():
        # Create posts
        posts = [
            Post(id=uuid4(), title=f"Complex {i}", content=f"Content {i}")
            for i in range(5)
        ]
        await post_repo.create_many(posts)

        # Query posts
        found_posts = await post_repo.where("title", "LIKE", "Complex%").get()

        # Count posts
        count = await post_repo.count()

        # Get tracker info
        tracker = Repository.get_query_tracker()
        return {
            "posts": found_posts,
            "count": count,
            "queries": tracker.get_queries() if tracker else [],
            "query_count": tracker.count() if tracker else 0,
        }

    result = await complex_operation()
    assert len(result["posts"]) == 5
    assert result["count"] == 5
    assert result["query_count"] == 3  # INSERT, SELECT, COUNT
    assert len(result["queries"]) == 3


@pytest.mark.asyncio
async def test_transactional_nested_with_query_logs():
    """Test nested @transactional decorators with query tracking"""
    post_repo = Repository(
        entity_schema_class=Post,
        entity_domain_class=Post,
        update_class=PostUpdate,
        table_name="posts",
    )

    @transactional(db_name="test_db", query_logs=True)
    async def outer_function():
        new_post = Post(id=uuid4(), title="Outer", content="Content")
        await post_repo.create(new_post)

        inner_result = await inner_function()

        tracker = Repository.get_query_tracker()
        return tracker.count() if tracker else 0, inner_result

    @transactional(db_name="test_db")
    async def inner_function():
        # This uses the same transaction and tracker from outer
        another_post = Post(id=uuid4(), title="Inner", content="Content")
        await post_repo.create(another_post)

        tracker = Repository.get_query_tracker()
        return tracker.count() if tracker else 0

    outer_count, inner_count = await outer_function()
    # Both should see the same tracker with accumulated queries
    assert outer_count == 2  # Two INSERTs
    assert inner_count == 2


@pytest.mark.asyncio
async def test_transactional_exception_handling_with_query_logs():
    """Test that query logs are available even when exceptions occur"""
    post_repo = Repository(
        entity_schema_class=Post,
        entity_domain_class=Post,
        update_class=PostUpdate,
        table_name="posts",
    )
    queries_before_exception = []

    @transactional(db_name="test_db", query_logs=True)
    async def operation_that_fails():
        new_post = Post(id=uuid4(), title="Will Fail", content="Content")
        await post_repo.create(new_post)

        # Capture queries before exception
        tracker = Repository.get_query_tracker()
        if tracker:
            queries_before_exception.extend(tracker.get_queries())

        # Simulate an error
        raise ValueError("Simulated error")

    with pytest.raises(ValueError, match="Simulated error"):
        await operation_that_fails()

    # Queries were tracked before the exception
    assert len(queries_before_exception) == 1
    assert "INSERT INTO posts" in queries_before_exception[0].query


@pytest.mark.asyncio
async def test_transactional_with_arguments():
    """Test @transactional with function arguments"""
    post_repo = Repository(
        entity_schema_class=Post,
        entity_domain_class=Post,
        update_class=PostUpdate,
        table_name="posts",
    )

    @transactional(db_name="test_db", query_logs=True)
    async def create_post_with_title(title: str, content: str):
        new_post = Post(id=uuid4(), title=title, content=content)
        await post_repo.create(new_post)

        tracker = Repository.get_query_tracker()
        return tracker.count() if tracker else 0

    query_count = await create_post_with_title("Test Title", "Test Content")
    assert query_count == 1


@pytest.mark.asyncio
async def test_transactional_query_logs_export():
    """Test exporting queries from @transactional decorator"""
    post_repo = Repository(
        entity_schema_class=Post,
        entity_domain_class=Post,
        update_class=PostUpdate,
        table_name="posts",
    )

    @transactional(db_name="test_db", query_logs=True)
    async def operation_with_export():
        new_post = Post(id=uuid4(), title="Export Test", content="Content")
        await post_repo.create(new_post)

        tracker = Repository.get_query_tracker()
        if tracker:
            return tracker.to_dict()
        return []

    queries_dict = await operation_with_export()
    assert len(queries_dict) == 1
    assert "query" in queries_dict[0]
    assert "params" in queries_dict[0]
    assert "timestamp" in queries_dict[0]

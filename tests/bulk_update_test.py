from uuid import uuid4

import pytest

from src.db_context import transactional
from tests.post_entities import Post, PostUpdate
from tests.post_repository import PostRepository


@pytest.mark.asyncio
@transactional("test_db")
async def test_update_many_by_ids_returns_updated_entities():
    repo = PostRepository()

    # Arrange: create three posts
    posts = [
        Post(id=uuid4(), title="Title 1", content="C1"),
        Post(id=uuid4(), title="Title 2", content="C2"),
        Post(id=uuid4(), title="Title 3", content="C3"),
    ]
    await repo.create_many(posts)

    ids_to_update = [posts[0].id, posts[1].id]
    update = PostUpdate(title="Updated", published=True)

    # Act
    updated = await repo.update_many_by_ids(ids_to_update, update)

    # Assert returned entities
    assert isinstance(updated, list)
    assert len(updated) == 2
    for ent in updated:
        assert ent.id in ids_to_update
        assert ent.title == "Updated"
        assert ent.published is True

    # Assert DB reflects changes
    fetched0 = await repo.find_by_id(posts[0].id)
    fetched1 = await repo.find_by_id(posts[1].id)
    fetched2 = await repo.find_by_id(posts[2].id)

    assert fetched0.title == "Updated" and fetched0.published is True
    assert fetched1.title == "Updated" and fetched1.published is True
    assert fetched2.title == "Title 3" and fetched2.published is False


@pytest.mark.asyncio
@transactional("test_db")
async def test_update_many_by_ids_with_empty_ids_returns_empty_list():
    repo = PostRepository()

    posts = [
        Post(id=uuid4(), title="A", content="A"),
        Post(id=uuid4(), title="B", content="B"),
    ]
    await repo.create_many(posts)

    result = await repo.update_many_by_ids([], PostUpdate(title="X"))
    assert result == []

    # Verify no changes occurred
    for p in posts:
        fetched = await repo.find_by_id(p.id)
        assert fetched.title == p.title


@pytest.mark.asyncio
@transactional("test_db")
async def test_update_many_by_ids_with_no_update_fields_makes_no_changes():
    repo = PostRepository()

    post = Post(id=uuid4(), title="Initial", content="C")
    await repo.create(post)

    # All fields None -> should be treated as no-op
    result = await repo.update_many_by_ids([post.id], PostUpdate())
    assert result == []

    fetched = await repo.find_by_id(post.id)
    assert fetched.title == "Initial"

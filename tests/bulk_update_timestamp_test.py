from datetime import datetime
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from pydantic import BaseModel

from src.db_context import transactional
from src.entities import BaseEntity
from src.repository import Repository


class TPost(BaseEntity):
    title: str
    content: str
    published: bool = False


class TPostSearch(BaseModel):
    id: UUID | None = None
    title: str | None = None
    content: str | None = None
    published: bool | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class TPostUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    published: bool | None = None


@pytest_asyncio.fixture
async def timestamped_repo(test_db_pool):
    # Ensure table exists with timestamp columns
    async with test_db_pool.acquire() as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS timestamped_posts (
                id UUID PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                content TEXT,
                published BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP WITH TIME ZONE,
                updated_at TIMESTAMP WITH TIME ZONE
            )
            """
        )

    from src.repository import RepositoryConfig

    return Repository(
        entity_schema_class=TPost,
        entity_domain_class=TPost,
        update_class=TPostUpdate,
        table_name="timestamped_posts",
        config=RepositoryConfig(timestamps=True),
    )


@pytest.mark.asyncio
@transactional("test_db")
async def test_update_many_sets_new_updated_at_for_all_rows(
    timestamped_repo: Repository[TPost, TPost, TPostUpdate],
):
    # Arrange
    posts = [
        TPost(id=uuid4(), title="A", content="a"),
        TPost(id=uuid4(), title="B", content="b"),
        TPost(id=uuid4(), title="C", content="c"),
    ]
    await timestamped_repo.create_many(posts)

    # Capture original timestamps by reading from DB to avoid any client-side timestamp reinjection skew
    originals: dict[UUID, tuple[datetime, datetime]] = {}
    for p in posts:
        fetched = await timestamped_repo.find_by_id(p.id)
        originals[p.id] = (fetched.created_at, fetched.updated_at)  # type: ignore[attr-defined]

    # Update a subset
    ids_to_update = [posts[0].id, posts[1].id]

    # Ensure time moves forward
    import time

    time.sleep(0.001)

    updated = await timestamped_repo.update_many_by_ids(
        ids_to_update, TPostUpdate(title="Z")
    )

    # Assert correct rows returned
    assert len(updated) == 2
    returned_ids = {u.id for u in updated}
    assert returned_ids == set(ids_to_update)

    # Verify updated_at is newer for all updated rows and created_at unchanged
    for u in updated:
        assert hasattr(u, "created_at") and hasattr(u, "updated_at")
        assert u.updated_at > originals[u.id][1]  # type: ignore[index]

        # fetch from DB and double-check created_at didn't change
        fetched = await timestamped_repo.find_by_id(u.id)
        assert fetched.created_at == originals[u.id][0]

    # Verify the non-updated row keeps the same updated_at
    not_updated_id = posts[2].id
    not_updated = await timestamped_repo.find_by_id(not_updated_id)
    assert not_updated.updated_at == originals[not_updated_id][1]

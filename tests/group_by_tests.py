from uuid import uuid4

import pytest

from src.db_context import transactional
from src.repository import Repository
from tests.post_entities import (
    Post as PostEntity,
)
from tests.post_entities import (
    PostSearch as PostSearchArgs,
)
from tests.post_entities import (
    PostUpdate as PostUpdateArgs,
)


class TestGroupByAndHaving:
    @pytest.fixture
    def repository(self):
        return Repository(PostEntity, PostSearchArgs, PostUpdateArgs, "posts")

    @pytest.mark.asyncio
    @transactional("test_db")
    async def test_group_by_basic_counts(self, repository):
        # Insert sample data
        posts = [
            PostEntity(
                id=uuid4(), title="A1", content="c", published=True, category="tech"
            ),
            PostEntity(
                id=uuid4(), title="A2", content="c", published=True, category="tech"
            ),
            PostEntity(
                id=uuid4(),
                title="B1",
                content="c",
                published=True,
                category="lifestyle",
            ),
            PostEntity(
                id=uuid4(), title="C1", content="c", published=False, category="tech"
            ),
        ]
        await repository.create_many(posts)

        # Select aggregated counts per category
        rows = (
            await repository.select("category", "COUNT(id) AS total")
            .group_by("category")
            .get()
        )

        # Convert to dict for easy lookup
        counts = {row["category"]: row["total"] for row in rows}
        assert counts["tech"] == 3
        assert counts["lifestyle"] == 1

    @pytest.mark.asyncio
    @transactional("test_db")
    async def test_group_by_having_filter(self, repository):
        # Insert sample data
        posts = [
            PostEntity(
                id=uuid4(), title="A1", content="c", published=True, category="tech"
            ),
            PostEntity(
                id=uuid4(), title="A2", content="c", published=True, category="tech"
            ),
            PostEntity(
                id=uuid4(),
                title="B1",
                content="c",
                published=True,
                category="lifestyle",
            ),
            PostEntity(
                id=uuid4(), title="C1", content="c", published=True, category="tech"
            ),
        ]
        await repository.create_many(posts)

        # Filter groups with count > 2
        rows = (
            await repository.select("category", "COUNT(id) AS total")
            .group_by("category")
            .having("COUNT(id)", ">", 2)
            .get()
        )

        assert len(rows) == 1
        assert rows[0]["category"] == "tech"
        assert rows[0]["total"] == 3

    @pytest.mark.asyncio
    @transactional("test_db")
    async def test_group_by_having_chaining_with_alias(self, repository):
        # Insert sample data to produce counts: tech=3, lifestyle=2, personal=1
        posts = [
            PostEntity(
                id=uuid4(), title="T1", content="c", published=True, category="tech"
            ),
            PostEntity(
                id=uuid4(), title="T2", content="c", published=True, category="tech"
            ),
            PostEntity(
                id=uuid4(), title="T3", content="c", published=True, category="tech"
            ),
            PostEntity(
                id=uuid4(),
                title="L1",
                content="c",
                published=True,
                category="lifestyle",
            ),
            PostEntity(
                id=uuid4(),
                title="L2",
                content="c",
                published=True,
                category="lifestyle",
            ),
            PostEntity(
                id=uuid4(), title="P1", content="c", published=True, category="personal"
            ),
        ]
        await repository.create_many(posts)

        # Chain HAVING conditions using the alias 'total'
        rows = (
            await repository.select("category", "COUNT(id) AS total")
            .group_by("category")
            .having("total", ">=", 2)
            .having("total", "<=", 2)
            .get()
        )

        assert len(rows) == 1
        assert rows[0]["category"] == "lifestyle"
        assert rows[0]["total"] == 2

    @pytest.mark.asyncio
    @transactional("test_db")
    async def test_group_by_having_chaining_mixed_alias_and_expression(
        self, repository
    ):
        # Insert sample data to produce counts: tech=3, lifestyle=2, personal=1
        posts = [
            PostEntity(
                id=uuid4(), title="T1", content="c", published=True, category="tech"
            ),
            PostEntity(
                id=uuid4(), title="T2", content="c", published=True, category="tech"
            ),
            PostEntity(
                id=uuid4(), title="T3", content="c", published=True, category="tech"
            ),
            PostEntity(
                id=uuid4(),
                title="L1",
                content="c",
                published=True,
                category="lifestyle",
            ),
            PostEntity(
                id=uuid4(),
                title="L2",
                content="c",
                published=True,
                category="lifestyle",
            ),
            PostEntity(
                id=uuid4(), title="P1", content="c", published=True, category="personal"
            ),
        ]
        await repository.create_many(posts)

        # Mix alias and raw expression in chained HAVING conditions
        rows = (
            await repository.select("category", "COUNT(id) AS total")
            .group_by("category")
            .having("total", ">", 1)
            .having("COUNT(id)", "<", 3)
            .get()
        )

        assert len(rows) == 1
        assert rows[0]["category"] == "lifestyle"
        assert rows[0]["total"] == 2

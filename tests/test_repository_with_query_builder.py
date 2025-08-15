"""
Tests for Repository fluent query builder functionality.
Tests the integration between Repository and QueryBuilder for fluent chaining.
"""

from uuid import uuid4

import pytest

from src.db_context import DatabaseManager, transactional
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


class TestRepositoryWithQueryBuilder:
    """Test suite for Repository fluent query builder functionality"""

    @pytest.fixture
    def repository(self):
        """Create a test repository instance"""
        return Repository(PostEntity, PostSearchArgs, PostUpdateArgs, "test_posts")

    @pytest.fixture
    def sample_posts(self):
        """Create sample test data"""
        return [
            {
                "id": uuid4(),
                "title": "Python Tutorial",
                "content": "Learn Python basics",
                "published": True,
                "category": "tech",
                "author_id": uuid4(),
            },
            {
                "id": uuid4(),
                "title": "JavaScript Guide",
                "content": "Learn JavaScript fundamentals",
                "published": True,
                "category": "tech",
                "author_id": uuid4(),
            },
            {
                "id": uuid4(),
                "title": "Draft Post",
                "content": "This is a draft",
                "published": False,
                "category": "personal",
                "author_id": uuid4(),
            },
            {
                "id": uuid4(),
                "title": "Cooking Tips",
                "content": "How to cook pasta",
                "published": True,
                "category": "lifestyle",
                "author_id": uuid4(),
            },
            {
                "id": uuid4(),
                "title": "Another Draft",
                "content": "Another draft post",
                "published": False,
                "category": "tech",
                "author_id": uuid4(),
            },
        ]

    async def setup_test_data(self, sample_posts):
        """Helper to set up test table and data"""
        conn = DatabaseManager.get_current_connection()
        if not conn:
            raise RuntimeError("No database connection available for test setup")

        # Create test table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS test_posts (
                id UUID PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                content TEXT NOT NULL,
                published BOOLEAN NOT NULL DEFAULT FALSE,
                category VARCHAR(100) NOT NULL,
                author_id UUID NOT NULL
            )
        """)

        # Clear existing data
        await conn.execute("DELETE FROM test_posts")

        # Insert test data
        for post in sample_posts:
            await conn.execute(
                """
                INSERT INTO test_posts (id, title, content, published, category, author_id)
                VALUES ($1, $2, $3, $4, $5, $6)
            """,
                post["id"],
                post["title"],
                post["content"],
                post["published"],
                post["category"],
                post["author_id"],
            )

    @pytest.mark.asyncio
    @transactional("test")
    async def test_basic_where_condition(self, repository, sample_posts):
        """Test basic WHERE condition using fluent interface"""
        await self.setup_test_data(sample_posts)

        # Test single WHERE condition
        published_posts = await repository.where("published", True).get()
        assert len(published_posts) == 3
        assert all(post.published for post in published_posts)

    @pytest.mark.asyncio
    @transactional("test")
    async def test_chained_where_conditions(self, repository, sample_posts):
        """Test chaining multiple WHERE conditions"""
        await self.setup_test_data(sample_posts)

        # Test chaining WHERE conditions
        tech_published = (
            await repository.where("category", "tech").where("published", True).get()
        )
        assert len(tech_published) == 2
        assert all(
            post.category == "tech" and post.published for post in tech_published
        )

    @pytest.mark.asyncio
    @transactional("test")
    async def test_where_with_operators(self, repository, sample_posts):
        """Test WHERE conditions with different operators"""
        await self.setup_test_data(sample_posts)

        # Test with different operators
        not_published = await repository.where("published", False, "=").get()
        assert len(not_published) == 2
        assert all(not post.published for post in not_published)

    @pytest.mark.asyncio
    @transactional("test")
    async def test_where_in_condition(self, repository, sample_posts):
        """Test WHERE IN condition"""
        await self.setup_test_data(sample_posts)

        # Test WHERE IN
        tech_lifestyle = await repository.where_in(
            "category", ["tech", "lifestyle"]
        ).get()
        assert len(tech_lifestyle) == 4
        assert all(post.category in ["tech", "lifestyle"] for post in tech_lifestyle)

    @pytest.mark.asyncio
    @transactional("test")
    async def test_where_not_in_condition(self, repository, sample_posts):
        """Test WHERE NOT IN condition"""
        await self.setup_test_data(sample_posts)

        # Test WHERE NOT IN
        not_tech = await repository.where_not_in("category", ["tech"]).get()
        assert len(not_tech) == 2
        assert all(post.category != "tech" for post in not_tech)

    @pytest.mark.asyncio
    @transactional("test")
    async def test_or_where_condition(self, repository, sample_posts):
        """Test OR WHERE condition"""
        await self.setup_test_data(sample_posts)

        # Test OR WHERE
        tech_or_lifestyle = (
            await repository.where("category", "tech")
            .or_where("category", "lifestyle")
            .get()
        )
        assert len(tech_or_lifestyle) == 4
        assert all(post.category in ["tech", "lifestyle"] for post in tech_or_lifestyle)

    @pytest.mark.asyncio
    @transactional("test")
    async def test_order_by_clause(self, repository, sample_posts):
        """Test ORDER BY clause"""
        await self.setup_test_data(sample_posts)

        # Test ORDER BY
        ordered_posts = await repository.order_by("title").get()
        assert len(ordered_posts) == 5
        titles = [post.title for post in ordered_posts]
        assert titles == sorted(titles)

    @pytest.mark.asyncio
    @transactional("test")
    async def test_limit_clause(self, repository, sample_posts):
        """Test LIMIT clause"""
        await self.setup_test_data(sample_posts)

        # Test LIMIT
        limited_posts = await repository.limit(3).get()
        assert len(limited_posts) == 3

    @pytest.mark.asyncio
    @transactional("test")
    async def test_offset_clause(self, repository, sample_posts):
        """Test OFFSET clause"""
        await self.setup_test_data(sample_posts)

        # Test OFFSET
        all_posts = await repository.get()
        offset_posts = await repository.offset(2).get()
        assert len(offset_posts) == len(all_posts) - 2

    @pytest.mark.asyncio
    @transactional("test")
    async def test_paginate_method(self, repository, sample_posts):
        """Test pagination"""
        await self.setup_test_data(sample_posts)

        # Test pagination
        page_1 = await repository.paginate(1, 2).get()
        page_2 = await repository.paginate(2, 2).get()
        page_3 = await repository.paginate(3, 2).get()

        assert len(page_1) == 2
        assert len(page_2) == 2
        assert len(page_3) == 1  # Last page with remaining record

    @pytest.mark.asyncio
    @transactional("test")
    async def test_complex_chaining(self, repository, sample_posts):
        """Test complex method chaining"""
        await self.setup_test_data(sample_posts)

        # Test complex chaining
        results = (
            await repository.where("published", True)
            .where_in("category", ["tech", "lifestyle"])
            .order_by_desc("title")
            .limit(2)
            .get()
        )

        assert len(results) == 2
        assert all(post.published for post in results)
        assert all(post.category in ["tech", "lifestyle"] for post in results)

    @pytest.mark.asyncio
    @transactional("test")
    async def test_first_method(self, repository, sample_posts):
        """Test first() method"""
        await self.setup_test_data(sample_posts)

        # Test first()
        first_tech = await repository.where("category", "tech").first()
        assert first_tech is not None
        assert first_tech.category == "tech"

        # Test first() with no results
        no_result = await repository.where("category", "nonexistent").first()
        assert no_result is None

    @pytest.mark.asyncio
    @transactional("test")
    async def test_count_method(self, repository, sample_posts):
        """Test count() method"""
        await self.setup_test_data(sample_posts)

        # Test count()
        total_count = await repository.count()
        assert total_count == 5

        published_count = await repository.where("published", True).count()
        assert published_count == 3

        tech_count = await repository.where("category", "tech").count()
        assert tech_count == 3

    @pytest.mark.asyncio
    @transactional("test")
    async def test_exists_method(self, repository, sample_posts):
        """Test exists() method"""
        await self.setup_test_data(sample_posts)

        # Test exists()
        has_published = await repository.where("published", True).exists()
        assert has_published is True

        has_nonexistent = await repository.where("category", "nonexistent").exists()
        assert has_nonexistent is False

    @pytest.mark.asyncio
    async def test_select_fields(self, repository):
        """Test custom SELECT fields"""
        # Test custom select - this will return raw rows, not entities
        # We test that the SQL is generated correctly
        sql = repository.select("title, category").where("published", True).to_sql()
        assert "SELECT title, category FROM test_posts" in sql
        assert "WHERE published = $1" in sql

    @pytest.mark.asyncio
    async def test_sql_generation(self, repository):
        """Test SQL generation methods"""
        # Test to_sql() method
        sql = repository.where("published", True).limit(10).to_sql()
        expected_parts = [
            "SELECT * FROM test_posts",
            "WHERE published = $1",
            "LIMIT 10",
        ]
        for part in expected_parts:
            assert part in sql

        # Test build() method
        query, params = (
            repository.where("category", "tech").where("published", True).build()
        )
        assert "SELECT * FROM test_posts" in query
        assert "WHERE category = $1 AND published = $2" in query
        assert params == ["tech", True]

    @pytest.mark.asyncio
    async def test_repository_immutability(self, repository):
        """Test that fluent methods don't mutate the original repository"""
        original_repo = repository

        # Create a new repository with conditions
        filtered_repo = repository.where("published", True)
        limited_repo = filtered_repo.limit(5)

        # Original repository should not have any query builder
        assert original_repo._query_builder is None

        # Each step should create a new repository instance
        assert filtered_repo is not original_repo
        assert limited_repo is not filtered_repo
        assert limited_repo is not original_repo

    @pytest.mark.asyncio
    @transactional("test")
    async def test_empty_repository_get(self, repository, sample_posts):
        """Test calling get() on repository without any conditions"""
        await self.setup_test_data(sample_posts)

        all_posts = await repository.get()
        assert len(all_posts) == 5

    @pytest.mark.asyncio
    @transactional("test")
    async def test_mixed_and_or_conditions(self, repository, sample_posts):
        """Test mixing AND and OR conditions"""
        await self.setup_test_data(sample_posts)

        # Test: (published = true) OR (category = 'personal')
        results = (
            await repository.where("published", True)
            .or_where("category", "personal")
            .get()
        )

        # Should get all published posts plus the personal draft
        assert len(results) == 4

    @pytest.mark.asyncio
    @transactional("test")
    async def test_query_builder_reset_between_calls(self, repository, sample_posts):
        """Test that query builder state doesn't leak between different query calls"""
        await self.setup_test_data(sample_posts)

        # First query
        tech_posts = await repository.where("category", "tech").get()
        assert len(tech_posts) == 3

        # Second query - should not inherit conditions from first
        all_posts = await repository.get()
        assert len(all_posts) == 5

        # Third query - should be independent
        published_posts = await repository.where("published", True).get()
        assert len(published_posts) == 3

    @pytest.mark.asyncio
    @transactional("test")
    async def test_method_chaining_order_independence(self, repository, sample_posts):
        """Test that method chaining order doesn't affect the final result for commutative operations"""
        await self.setup_test_data(sample_posts)

        # These should produce the same result
        result1 = (
            await repository.where("published", True).where("category", "tech").get()
        )
        result2 = (
            await repository.where("category", "tech").where("published", True).get()
        )

        assert len(result1) == len(result2) == 2

        # Sort by id to ensure same order for comparison
        result1_ids = sorted([str(post.id) for post in result1])
        result2_ids = sorted([str(post.id) for post in result2])
        assert result1_ids == result2_ids

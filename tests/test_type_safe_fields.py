"""
Tests for type-safe field definitions using SchemaBase and Field.

Verifies that Field objects can be used in place of string literals
for better IDE autocomplete, refactoring safety, and type checking.
"""

from uuid import uuid4

import pytest

from src.db_context import transactional
from src.entities import Field, SchemaBase
from src.query_builder import QueryBuilder
from src.repository import Repository
from tests.post_entities import Post as PostEntity
from tests.post_entities import PostUpdate as PostUpdateArgs


class PostSchema(SchemaBase):
    """Schema definition for posts table with type-safe fields"""

    id = Field[str]("id")
    title = Field[str]("title")
    content = Field[str]("content")
    published = Field[bool]("published")
    category = Field[str | None]("category")
    author_id = Field[str | None]("author_id")


class TestFieldClass:
    """Test the Field class itself"""

    def test_field_str_representation(self):
        """Test that Field objects return column name as string"""
        field = Field[str]("test_column")
        assert str(field) == "test_column"

    def test_field_repr(self):
        """Test Field repr representation"""
        field = Field[bool]("published")
        assert repr(field) == "Field(published)"

    def test_field_with_different_types(self):
        """Test Field objects with different type hints"""
        str_field = Field[str]("title")
        bool_field = Field[bool]("published")
        int_field = Field[int]("age")

        assert str(str_field) == "title"
        assert str(bool_field) == "published"
        assert str(int_field) == "age"


class TestQueryBuilderWithFields:
    """Test QueryBuilder with type-safe Field objects"""

    def test_where_with_field(self):
        """Test WHERE condition with Field object"""
        builder = QueryBuilder("posts")
        query, params = builder.where(PostSchema.published, True).build()

        assert query == "SELECT * FROM posts WHERE published = $1"
        assert params == [True]

    def test_where_with_field_and_operator(self):
        """Test WHERE condition with Field object and custom operator"""
        builder = QueryBuilder("posts")
        query, params = builder.where(PostSchema.title, "!=", "Draft").build()

        assert query == "SELECT * FROM posts WHERE title != $1"
        assert params == ["Draft"]

    def test_where_in_with_field(self):
        """Test WHERE IN with Field object"""
        builder = QueryBuilder("posts")
        query, params = builder.where_in(PostSchema.category, ["tech", "news"]).build()

        assert query == "SELECT * FROM posts WHERE category IN ($1, $2)"
        assert params == ["tech", "news"]

    def test_where_not_in_with_field(self):
        """Test WHERE NOT IN with Field object"""
        builder = QueryBuilder("posts")
        query, params = builder.where_not_in(PostSchema.category, ["draft"]).build()

        assert query == "SELECT * FROM posts WHERE category NOT IN ($1)"
        assert params == ["draft"]

    def test_or_where_with_field(self):
        """Test OR WHERE with Field object"""
        builder = QueryBuilder("posts")
        query, params = (
            builder.where(PostSchema.published, True)
            .or_where(PostSchema.category, "tech")
            .build()
        )

        assert query == "SELECT * FROM posts WHERE published = $1 OR category = $2"
        assert params == [True, "tech"]

    def test_order_by_with_field(self):
        """Test ORDER BY with Field object"""
        builder = QueryBuilder("posts")
        query, params = builder.order_by(PostSchema.title).build()

        assert query == "SELECT * FROM posts ORDER BY title"
        assert params == []

    def test_order_by_asc_with_field(self):
        """Test ORDER BY ASC with Field object"""
        builder = QueryBuilder("posts")
        query, params = builder.order_by_asc(PostSchema.title).build()

        assert query == "SELECT * FROM posts ORDER BY title"
        assert params == []

    def test_order_by_desc_with_field(self):
        """Test ORDER BY DESC with Field object"""
        builder = QueryBuilder("posts")
        query, params = builder.order_by_desc(PostSchema.published).build()

        assert query == "SELECT * FROM posts ORDER BY published DESC"
        assert params == []

    def test_group_by_with_field(self):
        """Test GROUP BY with Field objects"""
        builder = QueryBuilder("posts")
        query, params = builder.group_by(
            PostSchema.category, PostSchema.published
        ).build()

        assert query == "SELECT * FROM posts GROUP BY category, published"
        assert params == []

    def test_having_with_field(self):
        """Test HAVING with Field object"""
        builder = QueryBuilder("posts")
        query, params = (
            builder.select("COUNT(*) as cnt", "category")
            .group_by(PostSchema.category)
            .having(PostSchema.category, "!=", None)
            .build()
        )

        assert query == (
            "SELECT COUNT(*) as cnt, category FROM posts "
            "GROUP BY category HAVING category != $1"
        )
        assert params == [None]

    def test_mixed_string_and_field(self):
        """Test mixing string field names with Field objects"""
        builder = QueryBuilder("posts")
        query, params = (
            builder.where(PostSchema.published, True)
            .where("content", "!=", "")
            .order_by(PostSchema.title)
            .build()
        )

        assert (
            query
            == "SELECT * FROM posts WHERE published = $1 AND content != $2 ORDER BY title"
        )
        assert params == [True, ""]

    def test_complex_query_with_fields(self):
        """Test complex query using multiple Field objects"""
        builder = QueryBuilder("posts")
        query, params = (
            builder.where(PostSchema.published, True)
            .where_in(PostSchema.category, ["tech", "news"])
            .order_by_asc(PostSchema.title)
            .order_by_desc(PostSchema.category)
            .limit(10)
            .build()
        )

        assert (
            query
            == "SELECT * FROM posts WHERE published = $1 AND category IN ($2, $3) "
            "ORDER BY title, category DESC LIMIT 10"
        )
        assert params == [True, "tech", "news"]

    def test_select_with_field(self):
        """Test SELECT with Field object"""
        builder = QueryBuilder("posts")
        query, params = builder.select(PostSchema.id, PostSchema.title).build()

        assert query == "SELECT id, title FROM posts"
        assert params == []

    def test_select_with_mixed_string_and_field(self):
        """Test SELECT with mix of string and Field objects"""
        builder = QueryBuilder("posts")
        query, params = builder.select(
            "id", PostSchema.title, PostSchema.published
        ).build()

        assert query == "SELECT id, title, published FROM posts"
        assert params == []

    def test_select_single_field_object(self):
        """Test SELECT with a single Field object"""
        builder = QueryBuilder("posts")
        query, params = builder.select(PostSchema.title).build()

        assert query == "SELECT title FROM posts"
        assert params == []


class TestRepositoryWithFields:
    """Test Repository with type-safe Field objects"""

    @pytest.fixture
    def repository(self):
        """Create a test repository instance"""
        return Repository(
            entity_schema_class=PostEntity,
            entity_domain_class=PostEntity,
            update_class=PostUpdateArgs,
            table_name="test_posts",
        )

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
                "category": "draft",
                "author_id": uuid4(),
            },
        ]

    async def setup_test_data(self, sample_posts):
        """Helper method to insert test data into the database"""
        from src.db_context import DatabaseManager

        conn = DatabaseManager.get_current_connection()
        if not conn:
            return

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
    @transactional("test_db")
    async def test_repository_where_with_field(self, repository, sample_posts):
        """Test repository WHERE with Field object"""
        # Insert test data
        await self.setup_test_data(sample_posts)

        # Query using Field object
        posts = await repository.where(PostSchema.published, True).get()

        # Should return only published posts
        assert len(posts) == 2
        assert all(post.published for post in posts)

    @pytest.mark.asyncio
    @transactional("test_db")
    async def test_repository_where_in_with_field(self, repository, sample_posts):
        """Test repository WHERE IN with Field object"""
        # Insert test data
        await self.setup_test_data(sample_posts)

        # Query using Field object
        posts = await repository.where_in(PostSchema.category, ["tech"]).get()

        # Should return only tech posts
        assert len(posts) == 2
        assert all(post.category == "tech" for post in posts)

    @pytest.mark.asyncio
    @transactional("test_db")
    async def test_repository_order_by_with_field(self, repository, sample_posts):
        """Test repository ORDER BY with Field object"""
        # Insert test data
        await self.setup_test_data(sample_posts)

        # Query using Field object
        posts = await repository.order_by_asc(PostSchema.title).get()

        # Should be sorted by title
        titles = [post.title for post in posts]
        assert titles == ["Draft Post", "JavaScript Guide", "Python Tutorial"]

    @pytest.mark.asyncio
    @transactional("test_db")
    async def test_repository_complex_query_with_fields(self, repository, sample_posts):
        """Test repository complex query with Field objects"""
        # Insert test data
        await self.setup_test_data(sample_posts)

        # Complex query using Field objects
        posts = await (
            repository.where(PostSchema.published, True)
            .where_in(PostSchema.category, ["tech"])
            .order_by_asc(PostSchema.title)
            .get()
        )

        # Should return tech posts sorted by title
        assert len(posts) == 2
        assert posts[0].title == "JavaScript Guide"
        assert posts[1].title == "Python Tutorial"

    @pytest.mark.asyncio
    @transactional("test_db")
    async def test_repository_select_with_field(self, repository, sample_posts):
        """Test repository SELECT with Field object"""
        await self.setup_test_data(sample_posts)

        # Query using Field object in select
        results = await repository.select(PostSchema.id, PostSchema.title).get()

        # Should return dictionaries with only id and title
        assert len(results) == 3
        assert all("id" in result for result in results)
        assert all("title" in result for result in results)
        # Should NOT have other fields like content
        assert all("content" not in result for result in results)

    @pytest.mark.asyncio
    @transactional("test_db")
    async def test_repository_select_with_field_and_where(
        self, repository, sample_posts
    ):
        """Test repository SELECT with Field object combined with WHERE using Field"""
        await self.setup_test_data(sample_posts)

        # Query using Field objects in both select and where
        results = await (
            repository.select(PostSchema.id, PostSchema.title)
            .where(PostSchema.published, True)
            .get()
        )

        # Should return only published posts with id and title
        assert len(results) == 2
        assert all("id" in result for result in results)
        assert all("title" in result for result in results)

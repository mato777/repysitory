"""
Tests for ORDER BY clauses and complex query combinations.
"""

from uuid import uuid4

from src.query_builder import QueryBuilder


class TestOrderByAndComplexQueries:
    """Test cases for ORDER BY and complex query functionality"""

    def test_order_by_clause(self):
        """Test SELECT with ORDER BY"""
        builder = QueryBuilder("posts")
        query, params = builder.order_by("created_at DESC").build()

        assert query == "SELECT * FROM posts ORDER BY created_at DESC"
        assert params == []

    def test_complex_query(self):
        """Test complex query with all features"""
        post_id = uuid4()
        status = "published"
        builder = QueryBuilder("posts")
        query, params = (
            builder.select("title, content, created_at")
            .where("id", str(post_id))
            .where("status", status)
            .order_by("created_at DESC")
            .build()
        )

        expected_query = (
            "SELECT title, content, created_at FROM posts "
            "WHERE id = $1 AND status = $2 "
            "ORDER BY created_at DESC"
        )
        assert query == expected_query
        assert params == [str(post_id), status]

    def test_complex_query_with_all_clause_types(self):
        """Test complex query combining all types of clauses"""
        builder = QueryBuilder("posts")
        query, params = (
            builder.select("title, content, views")
            .where("published", True)
            .where_in("category", ["tech", "science"])
            .or_where("featured", True)
            .where_not_in("status", ["draft", "archived"])
            .order_by("views DESC, created_at ASC")
            .build()
        )

        expected_query = (
            "SELECT title, content, views FROM posts WHERE "
            "(published = $1 AND category IN ($2, $3) AND status NOT IN ($5, $6)) OR "
            "featured = $4 "
            "ORDER BY views DESC, created_at ASC"
        )
        assert query == expected_query
        assert params == [True, "tech", "science", True, "draft", "archived"]

    def test_complex_query_with_grouped_conditions(self):
        """Test complex query with grouped WHERE conditions"""

        def status_group(query):
            return query.where("status", "published").or_where("status", "featured")

        def category_group(query):
            return query.where_in("category", ["tech", "science"]).where("active", True)

        builder = QueryBuilder("posts")
        query, params = (
            builder.select("id, title, category, status")
            .where("user_id", "123")
            .where_group(status_group)
            .or_where_group(category_group)
            .order_by("created_at DESC")
            .build()
        )

        expected_query = (
            "SELECT id, title, category, status FROM posts WHERE "
            "(user_id = $1 AND (status = $2 OR status = $3)) OR "
            "(category IN ($4, $5) AND active = $6) "
            "ORDER BY created_at DESC"
        )
        assert query == expected_query
        assert params == ["123", "published", "featured", "tech", "science", True]

    def test_real_world_blog_query_example(self):
        """Test a realistic blog query with multiple conditions"""

        def visibility_conditions(query):
            return (
                query.where("published", True)
                .where("publish_date", "2023-01-01", "<=")
                .or_where("featured", True)
            )

        builder = QueryBuilder("posts")
        query, params = (
            builder.select("id, title, excerpt, author_id, created_at")
            .where("deleted_at", None, "IS")
            .where_in("category_id", [1, 2, 3, 5])
            .where_not_in("status", ["draft", "archived"])
            .where_group(visibility_conditions)
            .order_by("featured DESC, created_at DESC")
            .build()
        )

        expected_query = (
            "SELECT id, title, excerpt, author_id, created_at FROM posts WHERE "
            "deleted_at IS $1 AND category_id IN ($2, $3, $4, $5) AND "
            "status NOT IN ($6, $7) AND "
            "(published = $8 AND publish_date <= $9 OR featured = $10) "
            "ORDER BY featured DESC, created_at DESC"
        )
        assert query == expected_query
        assert params == [
            None,
            1,
            2,
            3,
            5,
            "draft",
            "archived",
            True,
            "2023-01-01",
            True,
        ]

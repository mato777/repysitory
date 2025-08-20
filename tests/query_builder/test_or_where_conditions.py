"""
Tests for OR WHERE conditions and mixed AND/OR logic.
"""

from src.query_builder import QueryBuilder


class TestOrWhereConditions:
    """Test cases for OR WHERE clause functionality"""

    def test_single_or_where_condition(self):
        """Test single OR WHERE condition"""
        builder = QueryBuilder("posts")
        query, params = builder.or_where("status", "draft").build()

        assert query == "SELECT * FROM posts WHERE status = $1"
        assert params == ["draft"]

    def test_multiple_or_where_conditions(self):
        """Test multiple OR WHERE conditions"""
        builder = QueryBuilder("posts")
        query, params = (
            builder.or_where("status", "draft")
            .or_where("status", "pending")
            .or_where("featured", True)
            .build()
        )

        assert (
            query
            == "SELECT * FROM posts WHERE (status = $1 OR status = $2 OR featured = $3)"
        )
        assert params == ["draft", "pending", True]

    def test_mixed_and_or_conditions(self):
        """Test mixing AND and OR conditions"""
        builder = QueryBuilder("posts")
        query, params = (
            builder.where("user_id", "123")
            .where("published", True)
            .or_where("status", "draft")
            .or_where("status", "pending")
            .build()
        )

        expected_query = "SELECT * FROM posts WHERE (user_id = $1 AND published = $2) OR (status = $3 OR status = $4)"
        assert query == expected_query
        assert params == ["123", True, "draft", "pending"]

    def test_or_where_multiple_list(self):
        """Test or_where_multiple with list of conditions"""
        builder = QueryBuilder("posts")
        conditions = [
            ("category", "=", "tech"),
            ("category", "=", "science"),
            ("priority", "=", "high"),
        ]
        query, params = builder.or_where_multiple(conditions).build()

        expected_query = "SELECT * FROM posts WHERE (category = $1 OR category = $2 OR priority = $3)"
        assert query == expected_query
        assert params == ["tech", "science", "high"]

    def test_or_where_any_single_condition(self):
        """Test or_where_any with a single condition tuple"""
        builder = QueryBuilder("posts")
        condition = ("status", "!=", "archived")
        query, params = builder.or_where_any(condition).build()

        assert query == "SELECT * FROM posts WHERE status != $1"
        assert params == ["archived"]

    def test_or_where_any_multiple_conditions(self):
        """Test or_where_any with multiple condition tuples"""
        builder = QueryBuilder("posts")
        conditions = [
            ("views", ">", 1000),
            ("likes", ">=", 100),
            ("featured", "=", True),
        ]
        query, params = builder.or_where_any(conditions).build()

        expected_query = (
            "SELECT * FROM posts WHERE (views > $1 OR likes >= $2 OR featured = $3)"
        )
        assert query == expected_query
        assert params == [1000, 100, True]

    def test_complex_mixed_conditions(self):
        """Test complex query with multiple AND groups and OR groups"""
        builder = QueryBuilder("posts")
        query, params = (
            builder.where("user_id", "123")
            .where("published", True)
            .where_multiple(
                [("created_at", ">", "2023-01-01"), ("updated_at", "<", "2023-06-01")]
            )
            .or_where("status", "=", "featured")
            .or_where_multiple(
                [("priority", "=", "urgent"), ("category", "=", "breaking")]
            )
            .build()
        )

        expected_query = (
            "SELECT * FROM posts WHERE "
            "(user_id = $1 AND published = $2 AND created_at > $3 AND updated_at < $4) OR "
            "(status = $5 OR priority = $6 OR category = $7)"
        )
        assert query == expected_query
        assert params == [
            "123",
            True,
            "2023-01-01",
            "2023-06-01",
            "featured",
            "urgent",
            "breaking",
        ]

"""
Tests for WHERE IN and WHERE NOT IN conditions.
"""

from src.query_builder import QueryBuilder


class TestInConditions:
    """Test cases for IN and NOT IN clause functionality"""

    def test_where_in_single_value(self):
        """Test WHERE IN with a single value"""
        builder = QueryBuilder("posts")
        query, params = builder.where_in("id", "123").build()

        assert query == "SELECT * FROM posts WHERE id IN ($1)"
        assert params == ["123"]

    def test_where_in_multiple_values(self):
        """Test WHERE IN with multiple values"""
        builder = QueryBuilder("posts")
        query, params = builder.where_in("id", ["123", "456", "789"]).build()

        assert query == "SELECT * FROM posts WHERE id IN ($1, $2, $3)"
        assert params == ["123", "456", "789"]

    def test_where_not_in_single_value(self):
        """Test WHERE NOT IN with a single value"""
        builder = QueryBuilder("posts")
        query, params = builder.where_not_in("status", "draft").build()

        assert query == "SELECT * FROM posts WHERE status NOT IN ($1)"
        assert params == ["draft"]

    def test_where_not_in_multiple_values(self):
        """Test WHERE NOT IN with multiple values"""
        builder = QueryBuilder("posts")
        query, params = builder.where_not_in(
            "status", ["draft", "archived", "deleted"]
        ).build()

        assert query == "SELECT * FROM posts WHERE status NOT IN ($1, $2, $3)"
        assert params == ["draft", "archived", "deleted"]

    def test_or_where_in_conditions(self):
        """Test OR WHERE IN conditions"""
        builder = QueryBuilder("posts")
        query, params = (
            builder.where("published", True)
            .or_where_in("category", ["tech", "science"])
            .build()
        )

        assert (
            query == "SELECT * FROM posts WHERE published = $1 OR category IN ($2, $3)"
        )
        assert params == [True, "tech", "science"]

    def test_or_where_not_in_conditions(self):
        """Test OR WHERE NOT IN conditions"""
        builder = QueryBuilder("posts")
        query, params = (
            builder.where("user_id", "123")
            .or_where_not_in("status", ["banned", "suspended"])
            .build()
        )

        assert (
            query == "SELECT * FROM posts WHERE user_id = $1 OR status NOT IN ($2, $3)"
        )
        assert params == ["123", "banned", "suspended"]

    def test_mixed_conditions_with_in_clauses(self):
        """Test mixing regular WHERE conditions with IN/NOT IN clauses"""
        builder = QueryBuilder("posts")
        query, params = (
            builder.where("published", True)
            .where_in("category", ["tech", "science"])
            .where_not_in("status", ["draft", "archived"])
            .where("views", ">", 1000)
            .build()
        )

        expected_query = (
            "SELECT * FROM posts WHERE "
            "published = $1 AND category IN ($2, $3) AND "
            "status NOT IN ($4, $5) AND views > $6"
        )
        assert query == expected_query
        assert params == [True, "tech", "science", "draft", "archived", 1000]

    def test_complex_in_with_or_conditions(self):
        """Test complex query with IN clauses and OR conditions"""
        builder = QueryBuilder("posts")
        query, params = (
            builder.where("published", True)
            .where_in("category", ["tech", "science"])
            .or_where("featured", True)
            .or_where_in("priority", ["high", "urgent"])
            .build()
        )

        expected_query = (
            "SELECT * FROM posts WHERE "
            "(published = $1 AND category IN ($2, $3)) OR "
            "(featured = $4 OR priority IN ($5, $6))"
        )
        assert query == expected_query
        assert params == [True, "tech", "science", True, "high", "urgent"]

    def test_parameter_indexing_with_in_clauses(self):
        """Test that parameter indexing works correctly with IN clauses"""
        builder = QueryBuilder("posts")
        query, params = (
            builder.where("user_id", "user123")
            .where_in("category", ["tech", "science", "health"])
            .where("created_at", ">", "2023-01-01")
            .where_not_in("status", ["draft", "archived"])
            .build()
        )

        expected_query = (
            "SELECT * FROM posts WHERE "
            "user_id = $1 AND category IN ($2, $3, $4) AND "
            "created_at > $5 AND status NOT IN ($6, $7)"
        )
        assert query == expected_query
        assert params == [
            "user123",
            "tech",
            "science",
            "health",
            "2023-01-01",
            "draft",
            "archived",
        ]

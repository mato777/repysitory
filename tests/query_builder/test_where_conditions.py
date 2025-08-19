"""
Tests for WHERE conditions, operators, and parameter indexing.
"""

from uuid import uuid4

from src.query_builder import QueryBuilder


class TestWhereConditions:
    """Test cases for WHERE clause functionality"""

    def test_single_where_condition(self):
        """Test SELECT with single WHERE condition"""
        post_id = uuid4()
        builder = QueryBuilder("posts")
        query, params = builder.where("id", str(post_id)).build()

        assert query == "SELECT * FROM posts WHERE id = $1"
        assert params == [str(post_id)]

    def test_multiple_where_conditions(self):
        """Test SELECT with multiple WHERE conditions"""
        post_id = uuid4()
        status = "published"
        builder = QueryBuilder("posts")
        query, params = (
            builder.where("id", str(post_id)).where("status", status).build()
        )

        assert query == "SELECT * FROM posts WHERE id = $1 AND status = $2"
        assert params == [str(post_id), status]

    def test_where_with_different_operators(self):
        """Test WHERE conditions with different operators"""
        builder = QueryBuilder("posts")
        query, params = (
            builder.where("age", ">", 18)
            .where("status", "!=", "draft")
            .where("price", "<=", 100)
            .build()
        )

        assert (
            query
            == "SELECT * FROM posts WHERE age > $1 AND status != $2 AND price <= $3"
        )
        assert params == [18, "draft", 100]

    def test_parameter_indexing(self):
        """Test that parameters are correctly indexed"""
        builder = QueryBuilder("posts")
        query, params = (
            builder.where("user_id", "user123")
            .where("created_at", ">", "2023-01-01")
            .where("status", "!=", "published")
            .build()
        )

        expected_query = (
            "SELECT * FROM posts WHERE "
            "user_id = $1 AND created_at > $2 AND status != $3"
        )
        assert query == expected_query
        assert params == ["user123", "2023-01-01", "published"]

    def test_where_multiple_list(self):
        """Test WHERE with multiple conditions using where_multiple method"""
        builder = QueryBuilder("posts")
        conditions = [
            ("id", "=", "123"),
            ("status", "=", "published"),
            ("age", ">", 18),
        ]
        query, params = builder.where_multiple(conditions).build()

        expected_query = (
            "SELECT * FROM posts WHERE id = $1 AND status = $2 AND age > $3"
        )
        assert query == expected_query
        assert params == ["123", "published", 18]

    def test_where_any_single_condition(self):
        """Test where_any with a single condition tuple"""
        builder = QueryBuilder("posts")
        condition = ("status", "!=", "draft")
        query, params = builder.where_any(condition).build()

        assert query == "SELECT * FROM posts WHERE status != $1"
        assert params == ["draft"]

    def test_where_any_multiple_conditions(self):
        """Test where_any with a list of condition tuples"""
        builder = QueryBuilder("posts")
        conditions = [
            ("user_id", "=", "user123"),
            ("created_at", ">", "2023-01-01"),
            ("price", "<=", 100),
        ]
        query, params = builder.where_any(conditions).build()

        expected_query = (
            "SELECT * FROM posts WHERE user_id = $1 AND created_at > $2 AND price <= $3"
        )
        assert query == expected_query
        assert params == ["user123", "2023-01-01", 100]

    def test_mixed_where_methods(self):
        """Test mixing different where methods"""
        builder = QueryBuilder("posts")
        conditions = [("status", "=", "published"), ("age", ">=", 18)]
        query, params = (
            builder.where("id", "123")
            .where_multiple(conditions)
            .where("title", "My Post", "!=")
            .build()
        )

        expected_query = (
            "SELECT * FROM posts WHERE "
            "id = $1 AND status = $2 AND age >= $3 AND title != $4"
        )
        assert query == expected_query
        assert params == ["123", "published", 18, "My Post"]

    def test_where_multiple_with_default_operator(self):
        """Test where_multiple with tuples that have default operator"""
        builder = QueryBuilder("posts")
        # Test with tuples that assume equality by using a helper method
        conditions = [
            ("id", "=", "123"),
            ("status", "=", "published"),
            ("category_id", "=", "456"),
        ]
        query, params = builder.where_multiple(conditions).build()

        expected_query = (
            "SELECT * FROM posts WHERE id = $1 AND status = $2 AND category_id = $3"
        )
        assert query == expected_query
        assert params == ["123", "published", "456"]

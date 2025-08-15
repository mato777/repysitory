"""
Tests for basic QueryBuilder operations like SELECT, table names, and method chaining.
"""

from uuid import uuid4

from src.query_builder import QueryBuilder


class TestBasicOperations:
    """Test cases for basic QueryBuilder functionality"""

    def test_basic_select_all(self):
        """Test basic SELECT * FROM table"""
        builder = QueryBuilder("posts")
        query, params = builder.build()

        assert query == "SELECT * FROM posts"
        assert params == []

    def test_select_specific_fields(self):
        """Test SELECT with specific fields"""
        builder = QueryBuilder("posts")
        query, params = builder.select("title, content").build()

        assert query == "SELECT title, content FROM posts"
        assert params == []

    def test_different_table_names(self):
        """Test QueryBuilder with different table names"""
        # Test with users table
        users_builder = QueryBuilder("users")
        query, params = users_builder.select("name, email").build()
        assert query == "SELECT name, email FROM users"

        # Test with categories table
        categories_builder = QueryBuilder("categories")
        query, params = categories_builder.where("parent_id", "456").build()
        assert query == "SELECT * FROM categories WHERE parent_id = $1"
        assert params == ["456"]

    def test_fluent_interface_immutability(self):
        """Test that each method call returns a new QueryBuilder instance"""
        builder1 = QueryBuilder("posts")
        builder2 = builder1.select("title")
        builder3 = builder2.where("id", "123")

        # Each builder should be different instances
        assert builder1 is not builder2
        assert builder2 is not builder3
        assert builder1 is not builder3

        # Original builder should remain unchanged
        query1, params1 = builder1.build()
        assert query1 == "SELECT * FROM posts"
        assert params1 == []

        # Final builder should have all modifications
        query3, params3 = builder3.build()
        assert query3 == "SELECT title FROM posts WHERE id = $1"
        assert params3 == ["123"]

    def test_method_chaining_order(self):
        """Test that method chaining works in any order"""
        post_id = uuid4()

        # Order: select -> where -> order_by
        builder1 = QueryBuilder("posts")
        query1, params1 = (
            builder1.select("title")
            .where("id", str(post_id))
            .order_by_asc("created_at")
            .build()
        )

        # Order: where -> select -> order_by
        builder2 = QueryBuilder("posts")
        query2, params2 = (
            builder2.where("id", str(post_id))
            .select("title")
            .order_by_asc("created_at")
            .build()
        )

        # Both should produce the same result
        expected_query = "SELECT title FROM posts WHERE id = $1 ORDER BY created_at"
        assert query1 == expected_query
        assert query2 == expected_query
        assert params1 == params2 == [str(post_id)]

    def test_overriding_previous_values(self):
        """Test that later method calls override previous ones for select and order_by"""
        builder = QueryBuilder("posts")
        query, params = (
            builder.select("title")
            .select("content")  # This should override the previous select
            .order_by_asc("created_at")
            .order_by_desc("title")  # This should override the previous order_by
            .build()
        )

        assert query == "SELECT content FROM posts ORDER BY created_at, title DESC"
        assert params == []

    def test_empty_where_conditions(self):
        """Test that empty WHERE conditions don't break the query"""
        builder = QueryBuilder("posts")
        query, params = builder.select("*").order_by_asc("id").build()

        assert query == "SELECT * FROM posts ORDER BY id"
        assert params == []

    def test_string_representation(self):
        """Test the string representation of QueryBuilder"""
        builder = QueryBuilder("posts")
        builder = builder.where("id", "123").order_by_asc("title")

        str_repr = str(builder)
        assert "Query: SELECT * FROM posts WHERE id = $1 ORDER BY title" in str_repr
        assert "Params: ['123']" in str_repr

    def test_to_sql_method(self):
        """Test the to_sql() method returns only SQL without parameters"""
        builder = QueryBuilder("posts")

        # Simple query
        sql = builder.where("id", "123").to_sql()
        assert sql == "SELECT * FROM posts WHERE id = $1"

        # Complex query with multiple conditions
        complex_sql = (
            builder.select("title, content")
            .where("published", True)
            .or_where_in("category", ["tech", "science"])
            .order_by_desc("created_at")
            .to_sql()
        )

        expected_sql = (
            "SELECT title, content FROM posts WHERE "
            "published = $1 OR category IN ($2, $3) "
            "ORDER BY created_at DESC"
        )
        assert complex_sql == expected_sql

        # Verify to_sql() returns string, not tuple
        assert isinstance(sql, str)
        assert isinstance(complex_sql, str)

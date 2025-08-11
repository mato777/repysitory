"""
Tests for grouped WHERE conditions using functions.
"""

from src.query_builder import QueryBuilder


class TestGroupedConditions:
    """Test cases for grouped WHERE clause functionality"""

    def test_where_group_basic(self):
        """Test basic where_group functionality"""

        def group_conditions(query):
            return query.where("status", "draft").or_where("status", "pending")

        builder = QueryBuilder("posts")
        sql = builder.where("user_id", "123").where_group(group_conditions).to_sql()

        expected = (
            "SELECT * FROM posts WHERE user_id = $1 AND (status = $2 OR status = $3)"
        )
        assert sql == expected

    def test_where_group_laravel_example(self):
        """Test the Laravel-equivalent example"""

        def nested_conditions(query):
            return (
                query.where_in("category", ["tech", "science"])
                .or_where("featured", True)
                .or_where_in("priority", ["high", "urgent"])
            )

        builder = QueryBuilder("posts")
        query, params = (
            builder.where("published", True).where_group(nested_conditions).build()
        )

        expected_sql = (
            "SELECT * FROM posts WHERE published = $1 AND "
            "(category IN ($2, $3) OR featured = $4 OR priority IN ($5, $6))"
        )
        assert query == expected_sql
        assert params == [True, "tech", "science", True, "high", "urgent"]

    def test_or_where_group(self):
        """Test or_where_group functionality"""

        def group_conditions(query):
            return query.where("priority", "high").where("urgent", True)

        builder = QueryBuilder("posts")
        sql = builder.where("published", True).or_where_group(group_conditions).to_sql()

        expected = "SELECT * FROM posts WHERE published = $1 OR (priority = $2 AND urgent = $3)"
        assert sql == expected

    def test_multiple_groups(self):
        """Test multiple where groups"""

        def first_group(query):
            return query.where("status", "published").or_where("status", "featured")

        def second_group(query):
            return query.where_in("category", ["tech", "news"]).or_where(
                "priority", "high"
            )

        builder = QueryBuilder("posts")
        query, params = (
            builder.where("user_id", "123")
            .where_group(first_group)
            .where_group(second_group)
            .build()
        )

        expected_sql = (
            "SELECT * FROM posts WHERE "
            "user_id = $1 AND (status = $2 OR status = $3) AND "
            "(category IN ($4, $5) OR priority = $6)"
        )
        assert query == expected_sql
        assert params == ["123", "published", "featured", "tech", "news", "high"]

    def test_where_with_function_unified_api(self):
        """Test using where() with a function (unified API)"""

        def group_conditions(query):
            return query.where("status", "draft").or_where("status", "pending")

        builder = QueryBuilder("posts")
        sql = builder.where("user_id", "123").where(group_conditions).to_sql()

        expected = (
            "SELECT * FROM posts WHERE user_id = $1 AND (status = $2 OR status = $3)"
        )
        assert sql == expected

    def test_or_where_with_function_unified_api(self):
        """Test using or_where() with a function (unified API)"""

        def group_conditions(query):
            return query.where("priority", "high").where("urgent", True)

        builder = QueryBuilder("posts")
        sql = builder.where("published", True).or_where(group_conditions).to_sql()

        expected = "SELECT * FROM posts WHERE published = $1 OR (priority = $2 AND urgent = $3)"
        assert sql == expected

    def test_unified_api_complex_example(self):
        """Test complex query using unified API with both regular conditions and groups"""

        def status_group(query):
            return query.where("status", "published").or_where("status", "featured")

        def priority_group(query):
            return query.where_in("priority", ["high", "urgent"]).or_where(
                "featured", True
            )

        builder = QueryBuilder("posts")
        query, params = (
            builder.where("user_id", "123")
            .where(status_group)
            .or_where(priority_group)
            .build()
        )

        expected_sql = (
            "SELECT * FROM posts WHERE "
            "(user_id = $1 AND (status = $2 OR status = $3)) OR "
            "(priority IN ($4, $5) OR featured = $6)"
        )
        assert query == expected_sql
        assert params == ["123", "published", "featured", "high", "urgent", True]

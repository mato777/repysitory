"""
Tests for the QueryBuilder class.
"""

from uuid import uuid4

from src.query_builder import QueryBuilder


class TestQueryBuilder:
    """Test cases for QueryBuilder functionality"""

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
            builder.where("age", 18, ">")
            .where("status", "draft", "!=")
            .where("price", 100, "<=")
            .build()
        )

        assert (
            query
            == "SELECT * FROM posts WHERE age > $1 AND status != $2 AND price <= $3"
        )
        assert params == [18, "draft", 100]

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

    def test_parameter_indexing(self):
        """Test that parameters are correctly indexed"""
        builder = QueryBuilder("posts")
        query, params = (
            builder.where("user_id", "user123")
            .where("created_at", "2023-01-01", ">")
            .where("status", "published", "!=")
            .build()
        )

        expected_query = (
            "SELECT * FROM posts WHERE "
            "user_id = $1 AND created_at > $2 AND status != $3"
        )
        assert query == expected_query
        assert params == ["user123", "2023-01-01", "published"]

    def test_empty_where_conditions(self):
        """Test that empty WHERE conditions don't break the query"""
        builder = QueryBuilder("posts")
        query, params = builder.select("*").order_by("id").build()

        assert query == "SELECT * FROM posts ORDER BY id"
        assert params == []

    def test_string_representation(self):
        """Test the string representation of QueryBuilder"""
        builder = QueryBuilder("posts")
        builder = builder.where("id", "123").order_by("title")

        str_repr = str(builder)
        assert "Query: SELECT * FROM posts WHERE id = $1 ORDER BY title" in str_repr
        assert "Params: ['123']" in str_repr

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

    def test_method_chaining_order(self):
        """Test that method chaining works in any order"""
        post_id = uuid4()

        # Order: select -> where -> order_by
        builder1 = QueryBuilder("posts")
        query1, params1 = (
            builder1.select("title")
            .where("id", str(post_id))
            .order_by("created_at")
            .build()
        )

        # Order: where -> select -> order_by
        builder2 = QueryBuilder("posts")
        query2, params2 = (
            builder2.where("id", str(post_id))
            .select("title")
            .order_by("created_at")
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
            .order_by("created_at")
            .order_by("title DESC")  # This should override the previous order_by
            .build()
        )

        assert query == "SELECT content FROM posts ORDER BY title DESC"
        assert params == []

    def test_where_multiple_list(self):
        """Test WHERE with multiple conditions using where_multiple method"""
        builder = QueryBuilder("posts")
        conditions = [
            ("id", "123", "="),
            ("status", "published", "="),
            ("age", 18, ">"),
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
        condition = ("status", "draft", "!=")
        query, params = builder.where_any(condition).build()

        assert query == "SELECT * FROM posts WHERE status != $1"
        assert params == ["draft"]

    def test_where_any_multiple_conditions(self):
        """Test where_any with a list of condition tuples"""
        builder = QueryBuilder("posts")
        conditions = [
            ("user_id", "user123", "="),
            ("created_at", "2023-01-01", ">"),
            ("price", 100, "<="),
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
        conditions = [("status", "published", "="), ("age", 18, ">=")]
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
            ("id", "123", "="),
            ("status", "published", "="),
            ("category_id", "456", "="),
        ]
        query, params = builder.where_multiple(conditions).build()

        expected_query = (
            "SELECT * FROM posts WHERE id = $1 AND status = $2 AND category_id = $3"
        )
        assert query == expected_query
        assert params == ["123", "published", "456"]

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
            ("category", "tech", "="),
            ("category", "science", "="),
            ("priority", "high", "="),
        ]
        query, params = builder.or_where_multiple(conditions).build()

        expected_query = "SELECT * FROM posts WHERE (category = $1 OR category = $2 OR priority = $3)"
        assert query == expected_query
        assert params == ["tech", "science", "high"]

    def test_or_where_any_single_condition(self):
        """Test or_where_any with a single condition tuple"""
        builder = QueryBuilder("posts")
        condition = ("status", "archived", "!=")
        query, params = builder.or_where_any(condition).build()

        assert query == "SELECT * FROM posts WHERE status != $1"
        assert params == ["archived"]

    def test_or_where_any_multiple_conditions(self):
        """Test or_where_any with multiple condition tuples"""
        builder = QueryBuilder("posts")
        conditions = [
            ("views", 1000, ">"),
            ("likes", 100, ">="),
            ("featured", True, "="),
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
                [("created_at", "2023-01-01", ">"), ("updated_at", "2023-06-01", "<")]
            )
            .or_where("status", "featured")
            .or_where_multiple(
                [("priority", "urgent", "="), ("category", "breaking", "=")]
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
            .where("views", 1000, ">")
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
            .where("created_at", "2023-01-01", ">")
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
            .order_by("created_at DESC")
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

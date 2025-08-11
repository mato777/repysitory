"""
Tests for LIMIT, OFFSET, and pagination functionality in QueryBuilder.
"""

from src.query_builder import QueryBuilder


class TestPaginationFeatures:
    """Test cases for pagination functionality"""

    def test_limit_clause(self):
        """Test basic LIMIT functionality"""
        builder = QueryBuilder("posts")
        query, params = builder.limit(10).build()

        assert query == "SELECT * FROM posts LIMIT 10"
        assert params == []

    def test_offset_clause(self):
        """Test basic OFFSET functionality"""
        builder = QueryBuilder("posts")
        query, params = builder.offset(20).build()

        assert query == "SELECT * FROM posts OFFSET 20"
        assert params == []

    def test_limit_and_offset_together(self):
        """Test LIMIT and OFFSET used together"""
        builder = QueryBuilder("posts")
        query, params = builder.limit(10).offset(20).build()

        assert query == "SELECT * FROM posts LIMIT 10 OFFSET 20"
        assert params == []

    def test_pagination_with_where_and_order(self):
        """Test pagination combined with WHERE and ORDER BY clauses"""
        builder = QueryBuilder("posts")
        query, params = (
            builder.where("published", True)
            .order_by("created_at DESC")
            .limit(5)
            .offset(10)
            .build()
        )

        expected_query = (
            "SELECT * FROM posts WHERE published = $1 "
            "ORDER BY created_at DESC LIMIT 5 OFFSET 10"
        )
        assert query == expected_query
        assert params == [True]

    def test_paginate_basic(self):
        """Test basic paginate functionality"""
        builder = QueryBuilder("posts")
        query, params = builder.paginate(page=1, per_page=10).build()

        assert query == "SELECT * FROM posts LIMIT 10 OFFSET 0"
        assert params == []

    def test_paginate_second_page(self):
        """Test paginate for second page"""
        builder = QueryBuilder("posts")
        query, params = builder.paginate(page=2, per_page=10).build()

        assert query == "SELECT * FROM posts LIMIT 10 OFFSET 10"
        assert params == []

    def test_paginate_third_page_custom_per_page(self):
        """Test paginate for third page with custom per_page"""
        builder = QueryBuilder("posts")
        query, params = builder.paginate(page=3, per_page=5).build()

        assert query == "SELECT * FROM posts LIMIT 5 OFFSET 10"
        assert params == []

    def test_paginate_default_per_page(self):
        """Test paginate with default per_page of 10"""
        builder = QueryBuilder("posts")
        query, params = builder.paginate(page=2).build()

        assert query == "SELECT * FROM posts LIMIT 10 OFFSET 10"
        assert params == []

    def test_paginate_with_complex_query(self):
        """Test paginate with complex query including WHERE, ORDER BY"""
        builder = QueryBuilder("posts")
        query, params = (
            builder.select("id, title, content")
            .where("published", True)
            .where_in("category", ["tech", "science"])
            .order_by("created_at DESC")
            .paginate(page=2, per_page=15)
            .build()
        )

        expected_query = (
            "SELECT id, title, content FROM posts WHERE "
            "published = $1 AND category IN ($2, $3) "
            "ORDER BY created_at DESC LIMIT 15 OFFSET 15"
        )
        assert query == expected_query
        assert params == [True, "tech", "science"]

    def test_paginate_overrides_previous_limit_offset(self):
        """Test that paginate overrides previously set limit/offset"""
        builder = QueryBuilder("posts")
        query, params = (
            builder.limit(100).offset(200).paginate(page=2, per_page=5).build()
        )

        # paginate should override the previous limit/offset
        assert query == "SELECT * FROM posts LIMIT 5 OFFSET 5"
        assert params == []

    def test_limit_offset_override_paginate(self):
        """Test that limit/offset can override paginate"""
        builder = QueryBuilder("posts")
        query, params = (
            builder.paginate(page=2, per_page=10).limit(25).offset(50).build()
        )

        # Later limit/offset should override paginate
        assert query == "SELECT * FROM posts LIMIT 25 OFFSET 50"
        assert params == []

    def test_paginate_validation_invalid_page(self):
        """Test paginate validation for invalid page numbers"""
        builder = QueryBuilder("posts")

        try:
            builder.paginate(page=0)
            raise AssertionError("Should have raised ValueError")
        except ValueError as e:
            assert "Page number must be 1 or greater" in str(e)

        try:
            builder.paginate(page=-1)
            raise AssertionError("Should have raised ValueError")
        except ValueError as e:
            assert "Page number must be 1 or greater" in str(e)

    def test_paginate_validation_invalid_per_page(self):
        """Test paginate validation for invalid per_page values"""
        builder = QueryBuilder("posts")

        try:
            builder.paginate(page=1, per_page=0)
            raise AssertionError("Should have raised ValueError")
        except ValueError as e:
            assert "Per page count must be 1 or greater" in str(e)

        try:
            builder.paginate(page=1, per_page=-5)
            raise AssertionError("Should have raised ValueError")
        except ValueError as e:
            assert "Per page count must be 1 or greater" in str(e)

    def test_fluent_interface_immutability_with_pagination(self):
        """Test that pagination methods maintain immutability"""
        builder1 = QueryBuilder("posts")
        builder2 = builder1.limit(10)
        builder3 = builder2.offset(20)
        builder4 = builder3.paginate(page=2, per_page=5)

        # Each builder should be different instances
        assert builder1 != builder2
        assert builder2 != builder3
        assert builder3 != builder4

        # Original builder should remain unchanged
        query1, params1 = builder1.build()
        assert query1 == "SELECT * FROM posts"
        assert params1 == []

        # Final builder should have pagination
        query4, params4 = builder4.build()
        assert query4 == "SELECT * FROM posts LIMIT 5 OFFSET 5"
        assert params4 == []

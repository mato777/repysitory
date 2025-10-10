from uuid import uuid4

import pytest

from tests.post_entities import Post, PostSearch, PostUpdate
from tests.post_repository import PostRepository


class TestRepositoryEdgeCases:
    """Test edge cases and error conditions in Repository"""

    @pytest.fixture
    def post_repo(self):
        """Create a test post repository instance."""
        return PostRepository()

    @pytest.mark.asyncio
    async def test_repository_method_without_transaction_context(self, post_repo):
        """Test that repository methods raise ValueError when called outside transaction context"""
        # This tests line 43 in repository.py - _get_connection() when no transaction is active
        with pytest.raises(
            ValueError,
            match="No active transaction found. Repository methods must be called within a transaction context.",
        ):
            await post_repo.find_by_id(uuid4())

    @pytest.mark.asyncio
    async def test_find_one_by_empty_search(self, post_repo):
        """Test that find_one_by returns None when search criteria is empty"""
        from src.db_context import transactional

        # This tests line 68 in repository.py - early return None when search_dict is empty
        @transactional("test_db")
        async def test_empty_search():
            # Create a search with all None values
            empty_search = PostSearch()  # All fields are None
            result = await post_repo.find_one_by(empty_search)
            assert result is None

        await test_empty_search()

    @pytest.mark.asyncio
    async def test_all_repository_methods_require_transaction_context(self, post_repo):
        """Test that all repository methods require transaction context"""
        sample_post = Post(id=uuid4(), title="Test", content="Test")
        sample_update = PostUpdate(title="Updated")
        sample_search = PostSearch(title="Test")

        # Test all methods that should require transaction context
        methods_to_test = [
            (post_repo.find_by_id, uuid4()),
            (post_repo.find_one_by, sample_search),
            (post_repo.find_many_by, None),
            (post_repo.create, sample_post),
            (post_repo.create_many, [sample_post]),
            (post_repo.update, uuid4(), sample_update),
            (post_repo.delete, uuid4()),
            (post_repo.delete_many, [uuid4()]),
        ]

        for method, *args in methods_to_test:
            with pytest.raises(ValueError, match="No active transaction found"):
                await method(*args)

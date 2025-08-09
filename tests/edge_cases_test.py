from uuid import uuid4

import pytest

from src.db_context import transactional
from tests.post_entities import Post, PostSearch, PostSort, PostUpdate
from tests.post_repository import PostRepository


class TestEdgeCasesAndValidation:
    """Test edge cases, error handling, and validation."""

    @pytest.fixture
    def post_repo(self):
        return PostRepository()

    @pytest.mark.asyncio
    @transactional("test")
    async def test_create_empty_list(self, post_repo, clean_db):
        """Test creating an empty list of posts."""
        result = await post_repo.create_many([])
        assert result == []

    @pytest.mark.asyncio
    @transactional("test")
    async def test_delete_empty_list(self, post_repo, clean_db):
        """Test deleting an empty list of IDs."""
        result = await post_repo.delete_many([])
        assert result == 0

    @pytest.mark.asyncio
    @transactional("test")
    async def test_delete_non_existent_ids(self, post_repo, clean_db):
        """Test deleting non-existent posts."""
        non_existent_ids = [uuid4(), uuid4()]
        deleted_count = await post_repo.delete_many(non_existent_ids)
        assert deleted_count == 0

    @pytest.mark.asyncio
    @transactional("test")
    async def test_update_non_existent_post(self, post_repo, clean_db):
        """Test updating a non-existent post."""
        non_existent_id = uuid4()
        result = await post_repo.update(non_existent_id, PostUpdate(title="New Title"))
        assert result is None

    @pytest.mark.asyncio
    @transactional("test")
    async def test_update_with_empty_data(self, post_repo, clean_db):
        """Test updating with empty data returns the original post."""
        post = Post(id=uuid4(), title="Original", content="Original content")
        await post_repo.create(post)

        result = await post_repo.update(post.id, PostUpdate())
        assert result is not None
        assert result.title == "Original"
        assert result.content == "Original content"

    @pytest.mark.asyncio
    @transactional("test")
    async def test_search_with_no_criteria(self, post_repo, clean_db):
        """Test searching with no criteria returns None for find_one_by."""
        # Create a post first
        post = Post(id=uuid4(), title="Test", content="Test content")
        await post_repo.create(post)

        # Search with empty criteria
        search = PostSearch()  # All fields are None
        result = await post_repo.find_one_by(search)
        assert result is None

    @pytest.mark.asyncio
    @transactional("test")
    async def test_sort_with_no_criteria(self, post_repo, clean_db):
        """Test sorting with no sort criteria."""
        posts = [
            Post(id=uuid4(), title="B", content="Content B"),
            Post(id=uuid4(), title="A", content="Content A"),
        ]
        await post_repo.create_many(posts)

        # Sort with empty criteria
        sort = PostSort()  # All fields are None
        result = await post_repo.find_many_post_by(sort=sort)
        assert len(result) == 2
        # Order should be insertion order since no sorting applied

    @pytest.mark.asyncio
    @transactional("test")
    async def test_mixed_partial_delete(self, post_repo, clean_db):
        """Test deleting a mix of existing and non-existent posts."""
        # Create some posts
        existing_posts = [
            Post(id=uuid4(), title="Exists 1", content="Content 1"),
            Post(id=uuid4(), title="Exists 2", content="Content 2"),
        ]
        await post_repo.create_many(existing_posts)

        # Try to delete existing and non-existing posts
        ids_to_delete = [
            existing_posts[0].id,  # Exists
            uuid4(),               # Doesn't exist
            existing_posts[1].id,  # Exists
            uuid4(),               # Doesn't exist
        ]

        deleted_count = await post_repo.delete_many(ids_to_delete)
        assert deleted_count == 2  # Only the existing ones should be deleted

    @pytest.mark.asyncio
    @transactional("test")
    async def test_large_batch_operations(self, post_repo, clean_db):
        """Test operations with larger batches."""
        # Create 100 posts
        posts = [
            Post(id=uuid4(), title=f"Post {i}", content=f"Content {i}")
            for i in range(100)
        ]

        # Test bulk create
        created_posts = await post_repo.create_many(posts)
        assert len(created_posts) == 100

        # Test bulk delete
        ids_to_delete = [post.id for post in posts[:50]]  # Delete first 50
        deleted_count = await post_repo.delete_many(ids_to_delete)
        assert deleted_count == 50

        # Verify remaining count
        remaining_posts = await post_repo.find_many_post_by()
        assert len(remaining_posts) == 50

    @pytest.mark.asyncio
    @transactional("test")
    async def test_uuid_consistency(self, post_repo, clean_db):
        """Test that UUIDs are handled consistently."""
        post_id = uuid4()
        post = Post(id=post_id, title="UUID Test", content="Testing UUID handling")

        # Create with specific UUID
        await post_repo.create(post)

        # Find by the same UUID
        found_post = await post_repo.find_by_id(post_id)
        assert found_post is not None
        assert found_post.id == post_id

        # Search by UUID
        search = PostSearch(id=post_id)
        found_by_search = await post_repo.find_one_by(search)
        assert found_by_search is not None
        assert found_by_search.id == post_id

    @pytest.mark.asyncio
    @transactional("test")
    async def test_special_characters_in_content(self, post_repo, clean_db):
        """Test handling of special characters in post content."""
        special_content = "Content with 'quotes', \"double quotes\", and $pecial ch@rs! 🚀"
        post = Post(
            id=uuid4(),
            title="Special Characters",
            content=special_content
        )

        await post_repo.create(post)
        found_post = await post_repo.find_by_id(post.id)

        assert found_post is not None
        assert found_post.content == special_content

    @pytest.mark.asyncio
    @transactional("test")
    async def test_long_content(self, post_repo, clean_db):
        """Test handling of very long content."""
        long_content = "A" * 10000  # 10KB of content
        post = Post(
            id=uuid4(),
            title="Long Content Test",
            content=long_content
        )

        await post_repo.create(post)
        found_post = await post_repo.find_by_id(post.id)

        assert found_post is not None
        assert found_post.content == long_content
        assert len(found_post.content) == 10000

import pytest
from uuid import uuid4
from src.db_context import transactional, DatabaseManager
from src.entities import SortOrder
from tests.post_entities import Post, PostSearch, PostSort, PostUpdate
from tests.post_repository import PostRepository


class TestPostRepositoryOperations:
    """Test all CRUD operations and search/sort functionality."""

    @pytest.fixture
    def post_repo(self):
        """Create a test post repository instance."""
        return PostRepository()

    @pytest.fixture
    def sample_posts(self):
        """Create sample posts for testing."""
        return [
            Post(id=uuid4(), title="First Post", content="This is the first post"),
            Post(id=uuid4(), title="Second Post", content="This is the second post"),
            Post(id=uuid4(), title="Third Post", content="This is the third post"),
            Post(id=uuid4(), title="Alpha Post", content="This comes first alphabetically"),
        ]

    @pytest.mark.asyncio
    @transactional("test")
    async def test_create_and_find_by_id(self, post_repo):
        """Test creating a post and finding it by ID."""
        # Create a post
        post = Post(id=uuid4(), title="Test Post", content="Test content")
        created_post = await post_repo.create(post)

        assert created_post.id == post.id
        assert created_post.title == post.title
        assert created_post.content == post.content

        # Find by ID
        found_post = await post_repo.find_by_id(post.id)
        assert found_post is not None
        assert found_post.id == post.id
        assert found_post.title == post.title
        assert found_post.content == post.content

    @pytest.mark.asyncio
    @transactional("test")
    async def test_find_by_id_not_found(self, post_repo, clean_db):
        """Test finding a non-existent post returns None."""
        non_existent_id = uuid4()
        found_post = await post_repo.find_by_id(non_existent_id)
        assert found_post is None

    @pytest.mark.asyncio
    @transactional("test")
    async def test_create_many(self, post_repo, sample_posts, clean_db):
        """Test creating multiple posts at once."""
        created_posts = await post_repo.create_many(sample_posts)

        assert len(created_posts) == len(sample_posts)

        # Verify all posts were created
        for original, created in zip(sample_posts, created_posts):
            assert created.id == original.id
            assert created.title == original.title
            assert created.content == original.content

            # Verify in database
            found_post = await post_repo.find_by_id(original.id)
            assert found_post is not None

    @pytest.mark.asyncio
    @transactional("test")
    async def test_find_one_by_search(self, post_repo, sample_posts, clean_db):
        """Test finding a single post using search criteria."""
        await post_repo.create_many(sample_posts)

        # Search by title
        search = PostSearch(title="First Post")
        found_post = await post_repo.find_one_by(search)

        assert found_post is not None
        assert found_post.title == "First Post"
        assert found_post.content == "This is the first post"

    @pytest.mark.asyncio
    @transactional("test")
    async def test_find_one_by_multiple_criteria(self, post_repo, sample_posts, clean_db):
        """Test finding a post with multiple search criteria."""
        await post_repo.create_many(sample_posts)

        # Search by title and content
        search = PostSearch(title="First Post", content="This is the first post")
        found_post = await post_repo.find_one_by(search)

        assert found_post is not None
        assert found_post.title == "First Post"

    @pytest.mark.asyncio
    @transactional("test")
    async def test_find_many_by_search(self, post_repo, sample_posts, clean_db):
        """Test finding multiple posts using search criteria."""
        await post_repo.create_many(sample_posts)

        # Find all posts (no search criteria)
        all_posts = await post_repo.find_many_post_by()
        assert len(all_posts) == len(sample_posts)

        # Search posts containing "Post" in title (should match all)
        # Note: This is exact match, not partial
        search = PostSearch()  # Empty search should return all
        found_posts = await post_repo.find_many_post_by(search)
        assert len(found_posts) == len(sample_posts)

    @pytest.mark.asyncio
    @transactional("test")
    async def test_sorting_single_field(self, post_repo, sample_posts, clean_db):
        """Test sorting by a single field."""
        await post_repo.create_many(sample_posts)

        # Sort by title ascending
        sort = PostSort(title=SortOrder.ASC)
        posts = await post_repo.find_many_post_by(sort=sort)

        titles = [post.title for post in posts]
        assert titles == sorted(titles)  # Should be alphabetically sorted
        assert titles[0] == "Alpha Post"  # Should come first alphabetically

    @pytest.mark.asyncio
    @transactional("test")
    async def test_sorting_descending(self, post_repo, sample_posts, clean_db):
        """Test sorting in descending order."""
        await post_repo.create_many(sample_posts)

        # Sort by title descending
        sort = PostSort(title=SortOrder.DESC)
        posts = await post_repo.find_many_post_by(sort=sort)

        titles = [post.title for post in posts]
        assert titles == sorted(titles, reverse=True)
        assert titles[0] == "Third Post"  # Should come first in reverse order

    @pytest.mark.asyncio
    @transactional("test")
    async def test_sorting_multiple_fields(self, post_repo, clean_db):
        """Test sorting by multiple fields."""
        # Create posts with same title but different content
        posts = [
            Post(id=uuid4(), title="Same Title", content="B Content"),
            Post(id=uuid4(), title="Same Title", content="A Content"),
            Post(id=uuid4(), title="Different Title", content="C Content"),
        ]
        await post_repo.create_many(posts)

        # Sort by title ASC, then content ASC
        sort = PostSort(title=SortOrder.ASC, content=SortOrder.ASC)
        sorted_posts = await post_repo.find_many_post_by(sort=sort)

        # Different Title should come first, then Same Title posts sorted by content
        assert sorted_posts[0].title == "Different Title"
        assert sorted_posts[1].title == "Same Title"
        assert sorted_posts[1].content == "A Content"  # A before B
        assert sorted_posts[2].title == "Same Title"
        assert sorted_posts[2].content == "B Content"

    @pytest.mark.asyncio
    @transactional("test")
    async def test_search_and_sort_combined(self, post_repo, clean_db):
        """Test combining search criteria with sorting."""
        posts = [
            Post(id=uuid4(), title="Test A", content="shared content"),
            Post(id=uuid4(), title="Test B", content="shared content"),
            Post(id=uuid4(), title="Other", content="different content"),
        ]
        await post_repo.create_many(posts)

        # Search for posts with shared content, sorted by title
        search = PostSearch(content="shared content")
        sort = PostSort(title=SortOrder.ASC)
        found_posts = await post_repo.find_many_post_by(search=search, sort=sort)

        assert len(found_posts) == 2
        assert found_posts[0].title == "Test A"
        assert found_posts[1].title == "Test B"

    @pytest.mark.asyncio
    @transactional("test")
    async def test_update(self, post_repo, clean_db):
        """Test updating a post."""
        # Create a post
        post = Post(id=uuid4(), title="Original Title", content="Original content")
        await post_repo.create(post)

        # Update the post using typed update model
        update_data = PostUpdate(title="Updated Title", content="Updated content")
        updated_post = await post_repo.update(post.id, update_data)

        assert updated_post is not None
        assert updated_post.id == post.id
        assert updated_post.title == "Updated Title"
        assert updated_post.content == "Updated content"

        # Verify in database
        found_post = await post_repo.find_by_id(post.id)
        assert found_post.title == "Updated Title"

    @pytest.mark.asyncio
    @transactional("test")
    async def test_delete(self, post_repo, clean_db):
        """Test deleting a post."""
        # Create a post
        post = Post(id=uuid4(), title="To Delete", content="Will be deleted")
        await post_repo.create(post)

        # Verify it exists
        found_post = await post_repo.find_by_id(post.id)
        assert found_post is not None

        # Delete the post
        deleted = await post_repo.delete(post.id)
        assert deleted is True

        # Verify it's gone
        found_post = await post_repo.find_by_id(post.id)
        assert found_post is None

    @pytest.mark.asyncio
    @transactional("test")
    async def test_delete_many(self, post_repo, sample_posts, clean_db):
        """Test deleting multiple posts."""
        await post_repo.create_many(sample_posts)

        # Delete first two posts
        ids_to_delete = [sample_posts[0].id, sample_posts[1].id]
        deleted_count = await post_repo.delete_many(ids_to_delete)

        assert deleted_count == 2

        # Verify they're gone
        for post_id in ids_to_delete:
            found_post = await post_repo.find_by_id(post_id)
            assert found_post is None

        # Verify remaining posts still exist
        remaining_posts = await post_repo.find_many_post_by()
        assert len(remaining_posts) == 2

    @pytest.mark.asyncio
    @transactional("test")
    async def test_convenience_methods(self, post_repo, sample_posts, clean_db):
        """Test convenience methods."""
        await post_repo.create_many(sample_posts)

        # Test find_by_title
        found_post = await post_repo.find_by_title("First Post")
        assert found_post is not None
        assert found_post.title == "First Post"

        # Test find_all_sorted_by_title
        sorted_posts = await post_repo.find_all_sorted_by_title()
        titles = [post.title for post in sorted_posts]
        assert titles == sorted(titles)

    @pytest.mark.asyncio
    @transactional("test")
    async def test_transaction_rollback(self, post_repo, clean_db):
        """Test that transactions rollback on error."""
        post = Post(id=uuid4(), title="Test", content="Test")

        try:
            async with DatabaseManager.transaction("test"):
                await post_repo.create(post)
                # Verify it exists within transaction
                found = await post_repo.find_by_id(post.id)
                assert found is not None

                # Force an error
                raise Exception("Force rollback")
        except Exception:
            pass  # Expected

        # Verify the post was rolled back
        found_post = await post_repo.find_by_id(post.id)
        assert found_post is None

    @pytest.mark.asyncio
    @transactional("test")
    async def test_transaction_commit(self, post_repo, clean_db):
        """Test that transactions commit successfully."""
        posts = [
            Post(id=uuid4(), title="Post 1", content="Content 1"),
            Post(id=uuid4(), title="Post 2", content="Content 2"),
        ]

        async with DatabaseManager.transaction("test"):
            await post_repo.create(posts[0])
            await post_repo.create(posts[1])
            # Both should be visible within the transaction
            found_posts = await post_repo.find_many_post_by()
            assert len(found_posts) == 2

        # Both should still exist after transaction commits
        found_posts = await post_repo.find_many_post_by()
        assert len(found_posts) == 2

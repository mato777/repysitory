"""
Example showing how to use the sorting functionality with the repository
"""
import asyncio
from uuid import uuid4
from entities import Post, PostSearch, PostSort, SortOrder
from post_repository import PostRepository

async def sorting_examples():
    """Examples of different sorting patterns"""

    post_repo = PostRepository()

    # Example 1: Simple single field sorting
    print("=== Single Field Sorting ===")

    # Sort by title ascending (default)
    sort = PostSort(title=SortOrder.ASC)
    posts = await post_repo.find_many_by(sort=sort)

    # Sort by title descending
    sort = PostSort(title=SortOrder.DESC)
    posts = await post_repo.find_many_by(sort=sort)


    # Example 2: Multi-field sorting
    print("=== Multi-Field Sorting ===")

    # Sort by title ASC, then by content DESC
    sort = PostSort(title=SortOrder.ASC, content=SortOrder.DESC)
    posts = await post_repo.find_many_by(sort=sort)
    # SQL: ORDER BY title ASC, content DESC


    # Example 3: Combining search with sorting
    print("=== Search + Sort ===")

    # Find posts with specific content, sorted by title
    search = PostSearch(content="tutorial")
    sort = PostSort(title=SortOrder.ASC)
    posts = await post_repo.find_many_by(search=search, sort=sort)
    # SQL: WHERE content = 'tutorial' ORDER BY title ASC


    # Example 4: Using convenience methods
    print("=== Convenience Methods ===")

    # Get all posts sorted by title
    posts = await post_repo.find_all_sorted_by_title()

    # Get latest posts (by ID descending)
    latest_posts = await post_repo.find_latest_posts()


    # Example 5: Type-safe field validation
    print("=== Type Safety ===")

    # ✅ This works - valid fields
    sort = PostSort(title=SortOrder.ASC, id=SortOrder.DESC)

    # ❌ This would cause IDE error - invalid field
    # sort = PostSort(invalid_field=SortOrder.ASC)  # Type error!


    # Example 6: Optional sorting (no sorting applied)
    print("=== Optional Sorting ===")

    # Get all posts without any sorting
    all_posts = await post_repo.find_many_by()

    # Search without sorting
    search = PostSearch(title="Hello")
    posts = await post_repo.find_many_by(search=search)


async def advanced_sorting_examples():
    """More advanced sorting scenarios"""

    post_repo = PostRepository()

    # Example 1: Complex business logic with sorting
    async def get_featured_posts():
        """Get posts sorted for a featured section"""
        search = PostSearch()  # No specific search criteria
        sort = PostSort(
            title=SortOrder.ASC,    # Primary sort: alphabetical
            id=SortOrder.DESC       # Secondary sort: newest first for same titles
        )
        return await post_repo.find_many_by(search=search, sort=sort)


    # Example 2: Transactional sorting
    async with post_repo.transaction():
        # All these operations share the same transaction
        search = PostSearch(content="important")
        sort = PostSort(title=SortOrder.ASC)

        important_posts = await post_repo.find_many_by(search=search, sort=sort)

        # Update posts in the same transaction
        for post in important_posts:
            await post_repo.update(post.id, {"content": f"[FEATURED] {post.content}"})


if __name__ == "__main__":
    asyncio.run(sorting_examples())
    asyncio.run(advanced_sorting_examples())

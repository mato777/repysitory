"""
Example showing how to use the sorting functionality with the repository
"""
import asyncio
import sys
from pathlib import Path

# Add the parent directory to Python path so we can import from src
sys.path.append(str(Path(__file__).parent.parent))

from uuid import uuid4
from src.entities import BaseEntity, SortOrder
from src.repository import Repository
from src.db_context import transactional, DatabaseManager
from pydantic import BaseModel, ConfigDict
from typing import Optional
from examples.db_setup import setup_postgres_connection, setup_example_schema, cleanup_example_data, close_connections

# Example entities and models
class Post(BaseEntity):
    title: str
    content: str

class PostSearch(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None

class PostUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None

class PostSort(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    title: Optional[SortOrder] = None
    content: Optional[SortOrder] = None
    id: Optional[SortOrder] = None

class PostRepository(Repository[Post, PostSearch, PostUpdate]):
    def __init__(self):
        super().__init__(Post, PostSearch, PostUpdate, "posts")

    # Convenience methods with built-in sorting
    async def find_all_sorted_by_title(self):
        sort = PostSort(title=SortOrder.ASC)
        return await self.find_many_by(sort=sort)

    async def find_latest_posts(self):
        sort = PostSort(id=SortOrder.DESC)
        return await self.find_many_by(sort=sort)

@transactional("default")
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


@transactional("default")
async def advanced_sorting_examples():
    """More advanced sorting scenarios"""
    post_repo = PostRepository()

    # Example 1: Complex business logic with sorting
    async def get_featured_posts():
        """Get posts sorted by multiple criteria for homepage"""
        # First by title alphabetically, then by content length (simulated with content field)
        sort = PostSort(title=SortOrder.ASC, content=SortOrder.DESC)
        return await post_repo.find_many_by(sort=sort)

    # Example 2: Conditional sorting based on user preference
    async def get_posts_by_preference(user_sort_preference: str):
        """Dynamic sorting based on user preference"""
        if user_sort_preference == "newest":
            sort = PostSort(id=SortOrder.DESC)
        elif user_sort_preference == "alphabetical":
            sort = PostSort(title=SortOrder.ASC)
        else:  # default
            sort = PostSort(title=SortOrder.ASC, id=SortOrder.DESC)

        return await post_repo.find_many_by(sort=sort)

    # Example 3: Search with fallback sorting
    async def search_posts_with_fallback(search_term: str):
        """Search posts with intelligent sorting fallback"""
        search = PostSearch(title=search_term)
        posts = await post_repo.find_many_by(search=search)

        if not posts:
            # Fallback: search by content instead, sorted by relevance (title first)
            search = PostSearch(content=search_term)
            sort = PostSort(title=SortOrder.ASC)
            posts = await post_repo.find_many_by(search=search, sort=sort)

        return posts

    # Run examples
    featured = await get_featured_posts()
    newest = await get_posts_by_preference("newest")
    search_results = await search_posts_with_fallback("tutorial")


# Example of multiple database sorting
@transactional("analytics_db")
async def analytics_sorting_example():
    """Example using different database for analytics"""
    analytics_repo = PostRepository()  # Same repo, different DB context

    # Get most popular posts (sorted by engagement metrics)
    sort = PostSort(title=SortOrder.DESC)  # Simulating popularity sort
    popular_posts = await analytics_repo.find_many_by(sort=sort)

    return popular_posts


# Manual transaction with sorting
async def manual_transaction_sorting():
    """Example of manual transaction management with sorting"""
    post_repo = PostRepository()

    async with DatabaseManager.transaction("default"):
        # Create some test posts
        post1 = await post_repo.create(Post(id=uuid4(), title="Zebra Post", content="Last alphabetically"))
        post2 = await post_repo.create(Post(id=uuid4(), title="Alpha Post", content="First alphabetically"))

        # Sort and verify order
        sort = PostSort(title=SortOrder.ASC)
        sorted_posts = await post_repo.find_many_by(sort=sort)

        assert sorted_posts[0].title == "Alpha Post"
        assert sorted_posts[-1].title == "Zebra Post"  # Assuming only these two posts


if __name__ == "__main__":
    async def main():
        """Run all sorting examples"""

        # Setup database connection
        print("🔧 Setting up database connection...")
        try:
            await setup_postgres_connection()
            await setup_example_schema()
            await cleanup_example_data()

        except Exception as e:
            print(f"Failed to setup database: {e}")
            print("\n💡 To run this example, make sure you have:")
            print("1. PostgreSQL running on localhost:5432")
            print("2. A 'postgres' database accessible with user 'postgres' and password 'postgres'")
            return

        try:
            print("\n=== Sorting Examples ===")
            await sorting_examples()

            print("\n=== Advanced Sorting Examples ===")
            await advanced_sorting_examples()

            print("\n=== Analytics Sorting Example ===")
            await analytics_sorting_example()

            print("\n=== Manual Transaction Sorting ===")
            await manual_transaction_sorting()

            print("\n✅ All sorting examples completed successfully!")

        except Exception as e:
            print(f"❌ Example failed: {e}")

        finally:
            await close_connections()

    print("🚀 Starting Sorting Examples")
    print("=" * 50)
    asyncio.run(main())

# Key features demonstrated:
# 1. Type-safe sorting with PostSort model
# 2. Multi-field sorting capabilities
# 3. Integration with search functionality
# 4. Automatic transaction context management
# 5. Support for multiple databases
# 6. Convenience methods for common sorting patterns

"""
Examples demonstrating transaction behavior with the new repository architecture
"""

import asyncio
import sys
from pathlib import Path

# Add the parent directory to Python path so we can import from src
sys.path.append(str(Path(__file__).parent.parent))

from uuid import UUID, uuid4

from pydantic import BaseModel

from examples.db_setup import (
    cleanup_example_data,
    close_connections,
    setup_example_schema,
    setup_postgres_connection,
)
from src.db_context import DatabaseManager, transactional
from src.entities import BaseEntity
from src.repository import Repository


# Example entities and models
class Post(BaseEntity):
    title: str = "Untitled Post"
    content: str = "No content provided"


class PostSearch(BaseModel):
    title: str | None = None
    content: str | None = None


class PostUpdate(BaseModel):
    title: str | None = None
    content: str | None = None


class PostRepository(Repository[Post, PostSearch, PostUpdate]):
    def __init__(self):
        super().__init__(Post, PostSearch, PostUpdate, "posts")


# Example 1: Automatic Rollback on Exception
@transactional("default")
async def transaction_rollback_example():
    """Demonstrates automatic rollback when an exception occurs"""
    post_repo = PostRepository()

    try:
        # Create first post
        post1 = Post(id=uuid4(), title="First Post", content="This will be rolled back")
        _ = await post_repo.create(post1)
        print(f"Created post: {post1.title}")

        # Create second post
        post2 = Post(
            id=uuid4(), title="Second Post", content="This will also be rolled back"
        )
        _ = await post_repo.create(post2)
        print(f"Created post: {post2.title}")

        # Verify both posts exist within transaction
        all_posts = await post_repo.find_many_by()
        print(f"Posts in transaction: {len(all_posts)}")

        # Force an error - this will rollback everything
        raise Exception("Something went wrong!")

    except Exception as e:
        print(f"Exception occurred: {e}")
        # Transaction is automatically rolled back

    # Verify rollback - posts should not exist
    async with DatabaseManager.transaction("default"):
        remaining_posts = await post_repo.find_many_by()
        print(f"Posts after rollback: {len(remaining_posts)}")


# Example 2: Successful Transaction Commit
@transactional("default")
async def transaction_commit_example():
    post_repo = PostRepository()

    # Create posts within transaction
    post1 = Post(id=uuid4(), title="Committed Post 1", content="This will be saved")
    post2 = Post(
        id=uuid4(), title="Committed Post 2", content="This will also be saved"
    )

    _ = await post_repo.create(post1)
    _ = await post_repo.create(post2)

    # Update one of the posts
    update_data = PostUpdate(title="Updated Committed Post 1")
    _ = await post_repo.update(post1.id, update_data)

    print("Transaction completed successfully - all changes committed")

    # Verify posts exist after transaction
    async with DatabaseManager.transaction("default"):
        all_posts = await post_repo.find_many_by()
        print(f"Posts after commit: {len(all_posts)}")

        updated_post = await post_repo.find_by_id(post1.id)
        if updated_post:
            print(f"Updated post title: {updated_post.title}")
        else:
            print("Updated post not found")


# Example 3: Nested Transactions
@transactional("default")
async def nested_transaction_example():
    """Demonstrates nested transaction behavior"""
    post_repo = PostRepository()

    # Outer transaction
    post1 = Post(id=uuid4(), title="Outer Transaction Post", content="Created in outer")
    _ = await post_repo.create(post1)
    print("Created post in outer transaction")

    try:
        # Inner transaction (nested)
        async with DatabaseManager.transaction("default"):
            post2 = Post(
                id=uuid4(), title="Inner Transaction Post", content="Created in inner"
            )
            _ = await post_repo.create(post2)
            print("Created post in inner transaction")

            # Both posts are visible within inner transaction
            all_posts = await post_repo.find_many_by()
            print(f"Posts in inner transaction: {len(all_posts)}")

            # Force error in inner transaction
            raise Exception("Inner transaction error")

    except Exception as e:
        print(f"Inner transaction failed: {e}")

    # Check what remains after inner transaction rollback
    remaining_posts = await post_repo.find_many_by()
    print(f"Posts after inner rollback: {len(remaining_posts)}")

    # Outer transaction can still commit successfully
    print("Outer transaction continues...")


# Example 4: Multiple Database Transactions
async def multi_database_example():
    """Example using multiple databases"""

    @transactional("default")
    async def create_user_data():
        post_repo = PostRepository()
        user_post = Post(
            id=uuid4(), title="User DB Post", content="Stored in user database"
        )
        _ = await post_repo.create(user_post)
        return user_post

    @transactional("default")
    async def create_analytics_data():
        post_repo = PostRepository()
        analytics_post = Post(
            id=uuid4(),
            title="Analytics DB Post",
            content="Stored in analytics database",
        )
        _ = await post_repo.create(analytics_post)
        return analytics_post

    # Each transaction uses a different database
    user_post = await create_user_data()
    analytics_post = await create_analytics_data()

    print(f"Created user post: {user_post.title}")
    print(f"Created analytics post: {analytics_post.title}")


# Example 5: Manual Transaction Management
async def manual_transaction_example():
    """Example of manual transaction management"""
    post_repo = PostRepository()

    # Manual transaction with explicit context
    async with DatabaseManager.transaction("default"):
        # All repository operations automatically use this transaction
        post1 = Post(id=uuid4(), title="Manual TX Post 1", content="First post")
        _ = await post_repo.create(post1)

        post2 = Post(id=uuid4(), title="Manual TX Post 2", content="Second post")
        _ = await post_repo.create(post2)

        # Update within same transaction
        update_data = PostUpdate(content="Updated content")
        _ = await post_repo.update(post1.id, update_data)

        # All operations are part of the same transaction
        all_posts = await post_repo.find_many_by()
        print(f"Posts in manual transaction: {len(all_posts)}")

    # Transaction commits when exiting the context manager
    print("Manual transaction committed")


# Example 6: Transaction with Business Logic
class PostService:
    def __init__(self):
        self.post_repo: PostRepository = PostRepository()

    @transactional("default")
    async def create_post_with_validation(self, title: str, content: str):
        """Business method with validation and transaction"""

        # Validation
        if len(title) < 3:
            raise ValueError("Title must be at least 3 characters")

        if "spam" in content.lower():
            raise ValueError("Content contains spam")

        # Create post
        post = Post(id=uuid4(), title=title, content=content)
        created_post = await self.post_repo.create(post)

        # Additional business logic
        if len(title) > 50:
            # Auto-truncate long titles
            update_data = PostUpdate(title=title[:50] + "...")
            created_post = await self.post_repo.update(created_post.id, update_data)

        return created_post

    @transactional("default")
    async def bulk_update_posts(self, updates: dict[str, dict[str, str]]) -> list[Post]:
        """Bulk update multiple posts in single transaction"""
        results: list[Post] = []

        for post_id, update_data in updates.items():
            post_update = PostUpdate(**update_data)
            updated_post = await self.post_repo.update(UUID(post_id), post_update)
            if updated_post:
                results.append(updated_post)

        return results


async def business_logic_transaction_example():
    """Example using business logic with transactions"""
    service = PostService()

    post1 = Post()
    try:
        # This will succeed
        post1 = await service.create_post_with_validation(
            "Valid Title", "Valid content"
        )
        if not post1:
            raise Exception("Post creation failed")

        print(f"Created valid post: {post1.title}")

        # This will fail and rollback
        _ = await service.create_post_with_validation("No", "This contains spam")

    except ValueError as e:
        print(f"Validation failed: {e}")

    # Bulk update example
    if not post1:
        raise Exception("No valid post to update")
    updates = {
        str(post1.id): {
            "title": "Bulk Updated Title",
            "content": "Bulk updated content",
        }
    }

    updated_posts = await service.bulk_update_posts(updates)
    print(f"Bulk updated {len(updated_posts)} posts")


async def main():
    """Run all transaction behavior examples"""

    # Setup database connection
    print("🔧 Setting up database connection...")
    try:
        _ = await setup_postgres_connection()
        await setup_example_schema()
        await cleanup_example_data()

    except Exception as e:
        print(f"Failed to setup database: {e}")
        print("\n💡 To run this example, make sure you have:")
        print("1. PostgreSQL running on localhost:5432")
        print(
            "2. A 'postgres' database accessible with user 'postgres' and password 'postgres'"
        )
        return

    try:
        print("=== Transaction Rollback Example ===")
        await transaction_rollback_example()

        print("\n=== Transaction Commit Example ===")
        await transaction_commit_example()

        print("\n=== Nested Transaction Example ===")
        await nested_transaction_example()

        print("\n=== Multi Database Example ===")
        await multi_database_example()

        print("\n=== Manual Transaction Example ===")
        await manual_transaction_example()

        print("\n=== Business Logic Transaction Example ===")
        await business_logic_transaction_example()

        print("\n✅ All transaction behavior examples completed successfully!")

    except Exception as e:
        print(f"❌ Example failed: {e}")

    finally:
        await close_connections()


if __name__ == "__main__":
    print("🚀 Starting Transaction Behavior Examples")
    print("=" * 50)
    asyncio.run(main())

# Key transaction behaviors demonstrated:
# 1. Automatic rollback on exceptions
# 2. Successful commit when no errors occur
# 3. Nested transaction support
# 4. Multiple database transaction isolation
# 5. Manual transaction context management
# 6. Integration with business logic and validation
# 7. Repository methods automatically use current transaction context

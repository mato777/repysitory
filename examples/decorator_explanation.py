"""
Examples showing the @transactional decorator and automatic transaction context management
"""

import asyncio
import sys
from pathlib import Path

# Add the parent directory to Python path so we can import from src
sys.path.append(str(Path(__file__).parent.parent))

from uuid import uuid4

from examples.db_setup import (
    cleanup_example_data,
    close_connections,
    setup_example_schema,
    setup_postgres_connection,
)
from examples.sample_data import Post, PostRepository, PostUpdate
from src.db_context import DatabaseManager, transactional


class PostService:
    def __init__(self):
        self.post_repo = PostRepository()

    # Example 1: Repository methods automatically use current transaction context
    # All methods must be called within a transaction

    @transactional("default")
    async def example_with_transaction(self):
        """All repository calls share the same transaction"""
        post1 = Post(id=uuid4(), title="Post 1", content="Content 1")
        await self.post_repo.create(post1)  # Uses transaction connection

        post2 = Post(id=uuid4(), title="Post 2", content="Content 2")
        await self.post_repo.create(post2)  # Uses same transaction connection

        # These ARE atomic - if post2 fails, post1 is also rolled back

    @transactional("default")
    async def example_with_different_database(self):
        """Repository calls use the 'analytics_db' database transaction"""
        post = Post(id=uuid4(), title="Analytics Post", content="Data content")
        await self.post_repo.create(post)

        # Update using typed update model
        update_data = PostUpdate(title="Updated Analytics Post")
        await self.post_repo.update(post.id, update_data)

    # Example 2: Manual transaction management
    async def complex_operation(self):
        """Manual transaction with automatic connection context"""
        async with DatabaseManager.transaction("default"):
            # Inside transaction - repository methods automatically use this connection
            post1 = await self.post_repo.create(
                Post(id=uuid4(), title="TX Post", content="Content")
            )

            # This also uses the same transaction connection automatically
            found_post = await self.post_repo.find_by_id(post1.id)

            if found_post:
                # Use typed update model
                update_data = PostUpdate(title="Updated in TX")
                await self.post_repo.update(found_post.id, update_data)

    # Example 3: Nested transactions
    @transactional("default")
    async def nested_transaction_example(self):
        """Outer transaction"""
        await self.post_repo.create(Post(id=uuid4(), title="Outer", content="Content"))

        # Inner transaction (nested)
        async with DatabaseManager.transaction("default"):
            await self.post_repo.create(
                Post(id=uuid4(), title="Inner", content="Content")
            )

            # Both posts are in the same transaction context
            posts = await self.post_repo.find_many_by()
            assert len(posts) >= 2

    # Example 4: Error handling and rollback
    @transactional("default")
    async def rollback_example(self):
        """Demonstrates automatic rollback on error"""
        try:
            post1 = await self.post_repo.create(
                Post(id=uuid4(), title="Will Rollback", content="Content")
            )

            # This will succeed
            update_data = PostUpdate(title="Updated Title")
            await self.post_repo.update(post1.id, update_data)

            # Force an error - this will rollback everything
            raise Exception("Something went wrong")

        except Exception:
            # The entire transaction is rolled back
            # post1 creation and update are both undone
            pass


async def main():
    """Run decorator explanation examples"""

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
        print(
            "2. A 'postgres' database accessible with user 'postgres' and password 'postgres'"
        )
        return

    try:
        service = PostService()

        print("\n=== Decorator Examples ===")

        # Example 1: Simple transactional method
        await service.example_with_transaction()

        # Example 2: Different database (will use same DB for demo)
        await service.example_with_different_database()

        # Example 3: Manual transaction
        await service.complex_operation()

        # Example 4: Nested transactions
        await service.nested_transaction_example()

        # Example 5: Error handling
        await service.rollback_example()

        print("\n✅ All decorator examples completed successfully!")

    except Exception as e:
        print(f"❌ Example failed: {e}")

    finally:
        await close_connections()


if __name__ == "__main__":
    print("🚀 Starting Decorator Examples")
    print("=" * 50)
    asyncio.run(main())

# Key differences from old approach:
# 1. No more manual connection passing
# 2. Repository methods automatically use current transaction context
# 3. @transactional decorator specifies which database to use
# 4. Typed update models provide compile-time safety
# 5. Repository must be called within transaction context (decorator or manual)

"""
Example usage of the context-based transaction system with database decorators
"""
import asyncio
import asyncpg
from uuid import uuid4
from entities import Post
from post_repository import PostRepository
from db_context import DatabaseManager, transactional, with_db


class PostService:
    def __init__(self):
        self.post_repo = PostRepository("default")
        self.analytics_repo = PostRepository("analytics")  # Different database

    @transactional("default")
    async def create_post_with_analytics(self, title: str, content: str):
        """
        This method automatically runs in a transaction on the 'default' database.
        The @transactional decorator ensures all repository operations share the same transaction.
        """
        # Create the main post
        post = Post(id=uuid4(), title=title, content=content)
        created_post = await self.post_repo.create(post)

        # Update some related data in the same transaction
        await self.post_repo.update(created_post.id, {"content": f"{content} [PROCESSED]"})

        return created_post

    @transactional("analytics")
    async def log_analytics(self, post_id: str, action: str):
        """
        This method runs in a transaction on the 'analytics' database
        """
        analytics_post = Post(
            id=uuid4(),
            title=f"Analytics: {action}",
            content=f"Post {post_id} - {action}"
        )
        return await self.analytics_repo.create(analytics_post)

    async def multi_database_operation(self, title: str, content: str):
        """
        Example of using multiple databases with explicit transaction management
        """
        # Transaction on default database
        async with DatabaseManager.transaction("default"):
            post = Post(id=uuid4(), title=title, content=content)
            created_post = await self.post_repo.create(post)

            # This will use the same transaction as above due to context
            await self.post_repo.update(created_post.id, {"title": f"[FINAL] {title}"})

        # Separate transaction on analytics database
        async with DatabaseManager.transaction("analytics"):
            await self.log_analytics(str(created_post.id), "created")

        return created_post


async def setup_databases():
    """Setup database pools for demonstration"""
    # Setup default database
    default_pool = await asyncpg.create_pool(
        "postgresql://user:password@localhost/main_db",
        min_size=1, max_size=10
    )
    await DatabaseManager.add_pool("default", default_pool)

    # Setup analytics database
    analytics_pool = await asyncpg.create_pool(
        "postgresql://user:password@localhost/analytics_db",
        min_size=1, max_size=5
    )
    await DatabaseManager.add_pool("analytics", analytics_pool)


async def main():
    """Example usage"""
    await setup_databases()

    service = PostService()

    # Example 1: Automatic transaction with decorator
    post1 = await service.create_post_with_analytics("Hello World", "This is content")
    print(f"Created post: {post1.title}")

    # Example 2: Multi-database operations
    post2 = await service.multi_database_operation("Multi DB", "Cross database content")
    print(f"Created post across databases: {post2.title}")

    # Example 3: Manual transaction control
    async with DatabaseManager.transaction("default") as conn:
        # All these operations share the same transaction
        post3 = Post(id=uuid4(), title="Manual TX", content="Manual transaction")
        await service.post_repo.create(post3, conn=conn)

        # Find and update in same transaction
        found_post = await service.post_repo.find_by_id(post3.id, conn=conn)
        if found_post:
            await service.post_repo.update(
                found_post.id,
                {"content": "Updated in transaction"},
                conn=conn
            )


if __name__ == "__main__":
    asyncio.run(main())

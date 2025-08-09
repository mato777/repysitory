"""
Example usage of the context-based transaction system with the new repository architecture
"""
import asyncio
from uuid import uuid4
from src.entities import BaseEntity
from src.repository import Repository
from src.db_context import DatabaseManager, transactional
from pydantic import BaseModel
from typing import Optional

# Example entities and models
class Post(BaseEntity):
    title: str
    content: str

class PostSearch(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None

class PostUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None

class PostRepository(Repository[Post, PostSearch, PostUpdate]):
    def __init__(self):
        super().__init__(Post, PostSearch, PostUpdate, "posts")

class PostService:
    def __init__(self):
        self.post_repo = PostRepository()

    @transactional("default")
    async def create_post_with_processing(self, title: str, content: str):
        """
        This method automatically runs in a transaction on the 'default' database.
        The @transactional decorator ensures all repository operations share the same transaction.
        """
        # Create the main post
        post = Post(id=uuid4(), title=title, content=content)
        created_post = await self.post_repo.create(post)

        # Update the post in the same transaction using typed update model
        update_data = PostUpdate(content=f"{content} [PROCESSED]")
        updated_post = await self.post_repo.update(created_post.id, update_data)

        return updated_post

    @transactional("analytics")
    async def log_analytics(self, post_id: str, action: str):
        """
        This method runs in a transaction on the 'analytics' database.
        Same repository, different database context.
        """
        analytics_post = Post(
            id=uuid4(),
            title=f"Analytics: {action}",
            content=f"Post {post_id} - {action}"
        )
        return await self.post_repo.create(analytics_post)

    async def multi_database_operation(self, title: str, content: str):
        """
        Example of using multiple databases with explicit transaction management
        """
        # Transaction on default database
        async with DatabaseManager.transaction("default"):
            post = Post(id=uuid4(), title=title, content=content)
            created_post = await self.post_repo.create(post)

            # Update within same transaction
            update_data = PostUpdate(title=f"[MAIN] {title}")
            main_post = await self.post_repo.update(created_post.id, update_data)

        # Separate transaction on analytics database
        async with DatabaseManager.transaction("analytics"):
            analytics_post = Post(
                id=uuid4(),
                title="Analytics Entry",
                content=f"Logged creation of post: {main_post.id}"
            )
            analytics_entry = await self.post_repo.create(analytics_post)

        return main_post, analytics_entry

    @transactional("default")
    async def bulk_operation(self, posts_data: list):
        """
        Bulk operation - all or nothing transaction
        """
        created_posts = []

        # Create multiple posts
        for post_data in posts_data:
            post = Post(id=uuid4(), **post_data)
            created_post = await self.post_repo.create(post)
            created_posts.append(created_post)

        # Update all posts with a common suffix
        for post in created_posts:
            update_data = PostUpdate(title=f"{post.title} [BATCH]")
            await self.post_repo.update(post.id, update_data)

        return created_posts

    async def complex_workflow(self, title: str, content: str):
        """
        Complex workflow with error handling and multiple transaction scopes
        """
        try:
            # Step 1: Create main content
            main_post = await self.create_post_with_processing(title, content)
            print(f"Created main post: {main_post.title}")

            # Step 2: Log analytics (separate transaction)
            analytics_post = await self.log_analytics(str(main_post.id), "created")
            print(f"Logged analytics: {analytics_post.title}")

            # Step 3: Additional processing in original database
            async with DatabaseManager.transaction("default"):
                # Find and update the post
                found_post = await self.post_repo.find_by_id(main_post.id)
                if found_post:
                    update_data = PostUpdate(content=f"{found_post.content} [WORKFLOW_COMPLETE]")
                    final_post = await self.post_repo.update(found_post.id, update_data)
                    print(f"Workflow completed: {final_post.content}")

            return final_post

        except Exception as e:
            print(f"Workflow failed: {e}")
            # Each transaction scope handles its own rollback
            raise

# Advanced usage examples
class AdvancedPostService:
    def __init__(self):
        self.post_repo = PostRepository()

    @transactional("default")
    async def create_with_validation(self, title: str, content: str):
        """Post creation with business validation"""
        # Business validation
        if len(title) < 5:
            raise ValueError("Title too short")

        if "forbidden" in content.lower():
            raise ValueError("Content contains forbidden words")

        # Create post
        post = Post(id=uuid4(), title=title, content=content)
        created_post = await self.post_repo.create(post)

        # Auto-format if needed
        if len(title) > 100:
            update_data = PostUpdate(title=title[:97] + "...")
            created_post = await self.post_repo.update(created_post.id, update_data)

        return created_post

    @transactional("default")
    async def archive_old_posts(self, days_old: int = 30):
        """Archive posts older than specified days"""
        # Find posts to archive (simplified - would normally check date)
        all_posts = await self.post_repo.find_many_by()

        archived_count = 0
        for post in all_posts:
            if "[ARCHIVED]" not in post.title:
                update_data = PostUpdate(title=f"[ARCHIVED] {post.title}")
                await self.post_repo.update(post.id, update_data)
                archived_count += 1

        return archived_count

async def main():
    """Demonstrate various transaction patterns"""
    service = PostService()
    advanced_service = AdvancedPostService()

    print("=== Basic Transaction Examples ===")

    # Example 1: Simple transactional method
    post1 = await service.create_post_with_processing("Example Post", "This is a test post")
    print(f"Created: {post1.title} - {post1.content}")

    # Example 2: Multi-database operation
    main_post, analytics_post = await service.multi_database_operation("Multi-DB Post", "Content for multiple databases")
    print(f"Main: {main_post.title}, Analytics: {analytics_post.title}")

    # Example 3: Bulk operation
    bulk_data = [
        {"title": "Bulk Post 1", "content": "First bulk post"},
        {"title": "Bulk Post 2", "content": "Second bulk post"},
        {"title": "Bulk Post 3", "content": "Third bulk post"}
    ]
    bulk_posts = await service.bulk_operation(bulk_data)
    print(f"Created {len(bulk_posts)} posts in bulk")

    # Example 4: Complex workflow
    final_post = await service.complex_workflow("Workflow Post", "Complex workflow content")
    print(f"Workflow result: {final_post.title}")

    print("\n=== Advanced Transaction Examples ===")

    # Example 5: Validation with rollback
    try:
        await advanced_service.create_with_validation("Test", "This content is forbidden")
    except ValueError as e:
        print(f"Validation failed (rolled back): {e}")

    # Example 6: Successful validation
    valid_post = await advanced_service.create_with_validation("Valid Long Title", "Valid content")
    print(f"Valid post created: {valid_post.title}")

    # Example 7: Bulk archive operation
    archived_count = await advanced_service.archive_old_posts()
    print(f"Archived {archived_count} posts")

if __name__ == "__main__":
    asyncio.run(main())

# Key patterns demonstrated:
# 1. @transactional decorator for automatic transaction management
# 2. Multiple database support with same repository
# 3. Manual transaction context management
# 4. Typed update models for safe updates
# 5. Complex workflows with multiple transaction scopes
# 6. Business logic integration with transaction boundaries
# 7. Error handling and automatic rollback
# 8. Bulk operations within transactions

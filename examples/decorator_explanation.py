"""
Examples showing the @transactional decorator and automatic transaction context management
"""
from uuid import uuid4
from src.entities import BaseEntity
from src.db_context import DatabaseManager, transactional
from src.repository import Repository
from pydantic import BaseModel
from typing import Optional


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

class PostRepository(Repository[Post, PostSearch, PostUpdate]):
    def __init__(self):
        super().__init__(Post, PostSearch, PostUpdate, "posts")


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

    @transactional("analytics_db")
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
            post1 = await self.post_repo.create(Post(id=uuid4(), title="TX Post", content="Content"))

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
        post1 = await self.post_repo.create(Post(id=uuid4(), title="Outer", content="Content"))

        # Inner transaction (nested)
        async with DatabaseManager.transaction("default"):
            post2 = await self.post_repo.create(Post(id=uuid4(), title="Inner", content="Content"))

            # Both posts are in the same transaction context
            posts = await self.post_repo.find_many_by()
            assert len(posts) >= 2

    # Example 4: Error handling and rollback
    @transactional("default")
    async def rollback_example(self):
        """Demonstrates automatic rollback on error"""
        try:
            post1 = await self.post_repo.create(Post(id=uuid4(), title="Will Rollback", content="Content"))

            # This will succeed
            update_data = PostUpdate(title="Updated Title")
            await self.post_repo.update(post1.id, update_data)

            # Force an error - this will rollback everything
            raise Exception("Something went wrong")

        except Exception:
            # The entire transaction is rolled back
            # post1 creation and update are both undone
            pass

# Key differences from old approach:
# 1. No more manual connection passing
# 2. Repository methods automatically use current transaction context
# 3. @transactional decorator specifies which database to use
# 4. Typed update models provide compile-time safety
# 5. Repository must be called within transaction context (decorator or manual)

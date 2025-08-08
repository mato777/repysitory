"""
Examples showing why we need both @with_db and @transactional decorators
"""
from uuid import uuid4
from entities import Post
from post_repository import PostRepository
from db_context import DatabaseManager, transactional, with_db


class PostService:
    def __init__(self):
        self.post_repo = PostRepository()

    # Example 1: Repository methods use @with_db
    # They work both inside and outside transactions

    async def example_without_transaction(self):
        """Each repository call gets its own connection"""
        post1 = Post(id=uuid4(), title="Post 1", content="Content 1")
        await self.post_repo.create(post1)  # Creates own connection

        post2 = Post(id=uuid4(), title="Post 2", content="Content 2")
        await self.post_repo.create(post2)  # Creates own connection

        # These are NOT atomic - if post2 fails, post1 is still created

    @transactional()
    async def example_with_transaction(self):
        """All repository calls share the same transaction"""
        post1 = Post(id=uuid4(), title="Post 1", content="Content 1")
        await self.post_repo.create(post1)  # Uses transaction connection

        post2 = Post(id=uuid4(), title="Post 2", content="Content 2")
        await self.post_repo.create(post2)  # Uses same transaction connection

        # These ARE atomic - if post2 fails, post1 is also rolled back

    # Example 2: Mixed usage
    async def complex_operation(self):
        """Manual transaction with automatic connection reuse"""
        async with DatabaseManager.transaction() as conn:
            # Inside transaction - @with_db will inject this connection
            post1 = await self.post_repo.create(Post(id=uuid4(), title="TX Post", content="Content"))

            # This also uses the same transaction connection automatically
            found_post = await self.post_repo.find_by_id(post1.id)

            if found_post:
                await self.post_repo.update(found_post.id, {"title": "Updated in TX"})

        # Outside transaction - each call gets its own connection
        await self.post_repo.find_by_id(post1.id)  # New connection


# Example 3: What if we only had @transactional?

class ServiceWithOnlyTransactional:
    def __init__(self):
        self.post_repo = PostRepository()

    @transactional()  # Every method call creates a transaction
    async def find_post(self, post_id):
        return await self.post_repo.find_by_id(post_id)

    @transactional()  # Another transaction
    async def update_post(self, post_id, data):
        return await self.post_repo.update(post_id, data)

    async def do_work(self):
        # Problem: These are separate transactions!
        post = await self.find_post(some_id)  # Transaction 1
        await self.update_post(some_id, data)  # Transaction 2

        # Not atomic! Update could fail while find succeeded


# Example 4: What if we only had @with_db?

class ServiceWithOnlyWithDb:
    def __init__(self):
        self.post_repo = PostRepository()

    async def atomic_operation(self):
        # Problem: How do we ensure atomicity?
        # We'd have to manually manage transactions everywhere
        async with DatabaseManager.transaction() as conn:
            await self.post_repo.create(post, conn=conn)  # Manual conn passing
            await self.post_repo.update(post_id, data, conn=conn)  # Manual conn passing
            # Verbose and error-prone


# Example 5: Perfect combination
class ServiceWithBoth:
    def __init__(self):
        self.post_repo = PostRepository()  # Uses @with_db

    @transactional()  # Manages transaction
    async def atomic_operation(self):
        # Repository methods automatically use the transaction connection
        # thanks to @with_db decorator
        post = await self.post_repo.create(some_post)
        await self.post_repo.update(post.id, some_data)
        # Clean, atomic, no manual connection passing!

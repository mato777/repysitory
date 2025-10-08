"""
Example demonstrating automatic timestamp functionality in Repository
"""

import asyncio
import sys
from pathlib import Path

# Add the parent directory to Python path so we can import from src
sys.path.append(str(Path(__file__).parent.parent))

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel

from examples.db_setup import (
    close_connections,
    setup_postgres_connection,
)
from src.db_context import DatabaseManager
from src.entities import BaseEntity
from src.repository import Repository


# Example entity with automatic timestamps
class BlogPost(BaseEntity):
    title: str
    content: str
    author: str
    published: bool = False


class BlogPostSearch(BaseModel):
    """Search model - includes timestamp fields for querying"""

    id: UUID | None = None
    title: str | None = None
    content: str | None = None
    author: str | None = None
    published: bool | None = None
    created_at: datetime | None = None  # Can search by creation time
    updated_at: datetime | None = None  # Can search by update time


class BlogPostUpdate(BaseModel):
    """Update model - timestamps are automatically handled"""

    title: str | None = None
    content: str | None = None
    author: str | None = None
    published: bool | None = None


async def demonstrate_timestamp_functionality():
    """Demonstrate automatic timestamp functionality"""

    # Setup database connection
    await setup_postgres_connection()
    db_manager = DatabaseManager()

    try:
        async with db_manager.transactional() as conn:
            # Create table with timestamp columns
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS blog_posts (
                    id UUID PRIMARY KEY,
                    title VARCHAR(255) NOT NULL,
                    content TEXT,
                    author VARCHAR(100),
                    published BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP WITH TIME ZONE,
                    updated_at TIMESTAMP WITH TIME ZONE
                )
            """)
            await conn.commit()

        # Create repository with timestamps enabled
        from src.repository import RepositoryConfig

        post_repo = Repository(
            entity_class=BlogPost,
            search_class=BlogPostSearch,
            update_class=BlogPostUpdate,
            table_name="blog_posts",
            config=RepositoryConfig(timestamps=True),  # Enable automatic timestamps
        )

        print("=== Automatic Timestamp Functionality Demo ===\n")

        # 1. Create a new blog post
        print("1. Creating a new blog post...")
        new_post = BlogPost(
            id=uuid4(),
            title="Getting Started with Python",
            content="Python is a versatile programming language...",
            author="John Doe",
        )

        created_post = await post_repo.create(new_post)
        print(f"   Created post: {created_post.title}")
        print(f"   Created at: {created_post.created_at}")
        print(f"   Updated at: {created_post.updated_at}")
        print(
            f"   Timestamps are equal on creation: {created_post.created_at == created_post.updated_at}"
        )
        print()

        # 2. Update the blog post
        print("2. Updating the blog post...")
        import time

        time.sleep(0.001)  # Small delay to ensure different timestamps

        update_data = BlogPostUpdate(
            title="Getting Started with Python - Updated", published=True
        )

        updated_post = await post_repo.update(created_post.id, update_data)
        print(f"   Updated post: {updated_post.title}")
        print(f"   Published: {updated_post.published}")
        print(f"   Created at: {updated_post.created_at}")
        print(f"   Updated at: {updated_post.updated_at}")
        print(
            f"   Created timestamp unchanged: {updated_post.created_at == created_post.created_at}"
        )
        print(
            f"   Updated timestamp changed: {updated_post.updated_at != created_post.updated_at}"
        )
        print()

        # 3. Create multiple posts
        print("3. Creating multiple posts...")
        posts = [
            BlogPost(
                id=uuid4(),
                title=f"Post {i}",
                content=f"Content for post {i}",
                author=f"Author {i}",
            )
            for i in range(1, 4)
        ]

        created_posts = await post_repo.create_many(posts)
        print(f"   Created {len(created_posts)} posts")
        for post in created_posts:
            print(f"   - {post.title} (created: {post.created_at})")
        print()

        # 4. Search by timestamp
        print("4. Searching by timestamp...")
        # Find posts created today
        today = datetime.now().strftime("%Y-%m-%d")
        _search_criteria = BlogPostSearch(created_at=f"{today}%")  # Posts created today

        # Note: This is a simplified search - in practice you'd use proper date range queries
        all_posts = await post_repo.find_many_by()
        print(f"   Found {len(all_posts)} total posts")
        for post in all_posts:
            print(
                f"   - {post.title} (created: {post.created_at}, updated: {post.updated_at})"
            )
        print()

        # 5. Demonstrate repository without timestamps
        print("5. Comparing with repository without timestamps...")

        # Create a repository without timestamps
        _no_timestamp_repo = Repository(
            entity_class=BlogPost,
            search_class=BlogPostSearch,
            update_class=BlogPostUpdate,
            table_name="blog_posts",
            config=RepositoryConfig(timestamps=False),  # Disable timestamps
        )

        _test_post = BlogPost(
            id=uuid4(),
            title="No Timestamp Test",
            content="This post won't have timestamps",
            author="Test Author",
        )

        # This would fail in practice because the table has timestamp columns
        # but the entity doesn't have timestamp fields
        print("   Repository without timestamps would not add timestamp fields")
        print("   (This is just for demonstration - actual usage would require")
        print("   a table without timestamp columns)")
        print()

        print("=== Demo Complete ===")
        print("\nKey Benefits of Automatic Timestamps:")
        print("- created_at and updated_at fields are automatically added to entities")
        print("- Timestamps are in datetime format (UTC)")
        print("- created_at is set once and never changes")
        print("- updated_at is updated on every modification")
        print("- Can search and filter by timestamp fields")
        print("- Consistent across create, update, and query operations")

    finally:
        await close_connections()


if __name__ == "__main__":
    asyncio.run(demonstrate_timestamp_functionality())

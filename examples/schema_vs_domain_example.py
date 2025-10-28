"""
Example demonstrating the separation between storage schema and domain entities.

This shows how you can have database entities with DB fields (created_at, updated_at)
that don't leak into your business logic domain.
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

from pydantic import BaseModel

# Add the parent directory to Python path so we can import from src
sys.path.append(str(Path(__file__).parent.parent))

from examples.db_setup import (
    cleanup_example_data,
    close_connections,
    setup_example_schema,
    setup_postgres_connection,
)
from src.db_context import transactional
from src.entities import BaseEntity
from src.repository import Repository

# ============================================================
# SCHEMA ENTITIES (Database Storage Representation)
# ============================================================


class PostSchema(BaseEntity):
    """Database schema - includes all DB fields including timestamps"""

    title: str
    content: str
    created_at: datetime
    updated_at: datetime
    # Could also include: deleted_at, created_by, updated_by, etc.


# ============================================================
# DOMAIN ENTITIES (Business Logic Representation)
# ============================================================


class Post(BaseModel):
    """Domain entity - clean business logic without DB noise"""

    id: UUID
    title: str
    content: str

    # Computed properties (not in database)
    @property
    def word_count(self) -> int:
        """Word count derived from content"""
        return len(self.content.split())

    @property
    def excerpt(self) -> str:
        """First 100 characters of content"""
        return self.content[:100] if len(self.content) > 100 else self.content


# ============================================================
# SEARCH AND UPDATE MODELS
# ============================================================


class PostSearch(BaseModel):
    """Search criteria for finding posts"""

    id: UUID | None = None
    title: str | None = None
    content: str | None = None


class PostUpdate(BaseModel):
    """Update model for posts"""

    title: str | None = None
    content: str | None = None


# ============================================================
# REPOSITORY WITH CUSTOM DOMAIN MAPPING
# ============================================================


class PostRepository(Repository[PostSchema, Post, PostUpdate]):
    """Repository that maps between schema and domain entities"""

    def __init__(self):
        super().__init__(
            entity_schema_class=PostSchema,
            entity_domain_class=Post,
            update_class=PostUpdate,
            table_name="posts",
        )

    def to_domain_entity(self, schema_entity: PostSchema) -> Post:
        """Custom mapping from database schema to domain entity

        This is where you filter out DB fields like created_at, updated_at
        and add computed properties.
        """
        return Post(
            id=schema_entity.id,
            title=schema_entity.title,
            content=schema_entity.content,
            # Note: word_count and excerpt are computed properties
        )


# ============================================================
# USAGE EXAMPLES
# ============================================================


@transactional("default")
async def schema_vs_domain_example():
    """Demonstrate schema vs domain entity separation"""

    repo = PostRepository()

    # Create a post (domain entity)
    domain_post = Post(
        id=uuid4(),
        title="Understanding Domain Models",
        content="This is a great article about domain-driven design and separating storage from business logic.",
    )

    print(f"Creating post: {domain_post.title}")
    print(f"Word count (domain): {domain_post.word_count}")
    print(f"Excerpt (domain): {domain_post.excerpt}")

    # When creating, we need to provide timestamps for the schema
    created_post = await repo.create(domain_post)

    print(f"\nCreated post ID: {created_post.id}")
    print(f"Word count (after create): {created_post.word_count}")
    print(f"Excerpt (after create): {created_post.excerpt}")

    # Find by ID - returns domain entity without DB fields
    found_post = await repo.find_by_id(created_post.id)
    if found_post:
        print(f"\nFound post: {found_post.title}")
        # Can access computed properties
        print(f"Word count: {found_post.word_count}")
        print(f"Excerpt: {found_post.excerpt}")

    # Update using domain entity fields only
    update_data = PostUpdate(
        content="Updated content with more words to demonstrate computed properties"
    )
    updated_post = await repo.update(created_post.id, update_data)

    if updated_post:
        print(f"\nUpdated post content: {updated_post.content}")
        print(f"New word count: {updated_post.word_count}")

    # Find all posts
    all_posts = await repo.get()
    print(f"\nTotal posts in database: {len(all_posts)}")

    # Show that domain entities don't have DB fields
    print("\n" + "=" * 50)
    print("KEY POINTS:")
    print("=" * 50)
    print("✓ Domain entities don't expose created_at, updated_at")
    print("✓ Domain entities have computed properties")
    print("✓ Schema entities are internal to the repository")
    print("✓ Public API returns clean domain entities")


async def main():
    """Run the example"""
    print("🚀 Schema vs Domain Entity Example\n")

    # Setup database
    try:
        await setup_postgres_connection()
        await setup_example_schema()

        # Run the example
        await schema_vs_domain_example()

        print("\n✅ Example completed successfully!")

    except Exception as e:
        print(f"❌ Example failed: {e}")
        import traceback

        traceback.print_exc()

    finally:
        await cleanup_example_data()
        await close_connections()


if __name__ == "__main__":
    asyncio.run(main())

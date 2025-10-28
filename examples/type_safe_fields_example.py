"""
Example demonstrating type-safe field definitions using SchemaBase and Field.

This allows developers to use typed field references instead of string literals
for better IDE autocomplete, refactoring safety, and type checking.

Usage:
    from src.entities import SchemaBase, Field

    class PostSchema(SchemaBase):
        published = Field[bool]("published")
        title = Field[str]("title")

    # Then use in queries:
    repo.where(PostSchema.published, True)
    repo.where_in(PostSchema.title, ["Title 1", "Title 2"])
"""

from src.entities import Field, SchemaBase
from src.repository import Repository
from tests.post_entities import Post


# Define a type-safe schema
class PostSchema(SchemaBase):
    """Schema definition for posts table with type-safe fields"""

    id = Field[str]("id")
    title = Field[str]("title")
    content = Field[str]("content")
    published = Field[bool]("published")
    created_at = Field[str]("created_at")  # datetime as string in DB
    updated_at = Field[str]("updated_at")


async def demonstrate_type_safe_fields():
    """Demonstrate type-safe field usage in queries"""

    # Create repository (using Post as both schema and domain for simplicity)
    post_repo = Repository(
        entity_schema_class=Post,
        entity_domain_class=Post,
        update_class=Post,
        table_name="posts",
    )

    # Example 1: Simple WHERE condition
    print("Example 1: Query published posts")
    posts = await post_repo.where("published", True).get()
    print(f"Found {len(posts)} published posts")

    # Example 2: WHERE IN
    print("\nExample 2: Query by title list")
    titles = ["Post 1", "Post 2"]
    posts = await post_repo.where_in("title", titles).get()
    print(f"Found {len(posts)} posts with specified titles")

    # Example 3: Complex query with multiple conditions
    print("\nExample 3: Complex query")
    posts = await (
        post_repo.where("published", True)
        .where_not_in("title", ["Draft"])
        .order_by_asc("title")
        .limit(10)
        .get()
    )
    print(f"Found {len(posts)} published posts (excluding drafts)")

    # Example 4: Chained WHERE and ORDER BY
    print("\nExample 4: Chained operations")
    posts = await post_repo.where("published", True).order_by_desc("created_at").first()
    print("Latest published post:", posts.title if posts else "None")

    # Example 5: Multiple WHERE conditions
    print("\nExample 5: Multiple WHERE conditions")
    posts = await post_repo.where("published", True).where("content", "!=", "").get()
    print(f"Found {len(posts)} posts with content")

    print("\n✅ Type-safe field examples completed!")


if __name__ == "__main__":
    import asyncio

    async def main():
        from examples.db_setup import setup_postgres_connection

        await setup_postgres_connection()
        await demonstrate_type_safe_fields()

    asyncio.run(main())

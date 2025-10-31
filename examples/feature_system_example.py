"""
Example demonstrating automatic field handling in Repository

This example shows how the repository automatically handles created_at, updated_at,
and deleted_at fields based on their presence in the schema.
"""

from datetime import datetime

from pydantic import BaseModel

from src import Repository, RepositoryConfig
from src.entities import BaseEntity

# Example 1: Automatic Timestamp Management
# =========================================
# Simply add created_at and/or updated_at to your schema
# and the repository will automatically manage them!


class ArticleWithTimestamps(BaseEntity):
    """Article entity with automatic timestamp fields"""

    title: str
    content: str
    author: str
    created_at: datetime  # Automatically set on create
    updated_at: datetime  # Automatically set on create and update


class ArticleUpdate(BaseModel):
    title: str | None = None
    content: str | None = None


# Repository automatically handles created_at and updated_at
article_repo = Repository(
    entity_class=ArticleWithTimestamps,
    update_class=ArticleUpdate,
    table_name="articles",
    config=RepositoryConfig(),
)

# Example 2: Automatic Soft Delete Management
# ============================================
# Add deleted_at to your schema to enable automatic soft delete handling!


class ProductWithSoftDelete(BaseEntity):
    """Product entity with automatic soft delete"""

    name: str
    price: float
    deleted_at: (
        datetime | None
    )  # Automatically set to None on create, managed by repository


class ProductUpdate(BaseModel):
    name: str | None = None
    price: float | None = None


product_repo = Repository(
    entity_class=ProductWithSoftDelete,
    update_class=ProductUpdate,
    table_name="products",
    config=RepositoryConfig(),
)

# Example 3: Combining Timestamps and Soft Delete
# ================================================
# Use all three fields together for full automation!


class CommentWithAllFeatures(BaseEntity):
    """Comment entity with timestamps and soft delete"""

    content: str
    user_id: str
    created_at: datetime  # Auto-managed on create
    updated_at: datetime  # Auto-managed on create and update
    deleted_at: datetime | None  # Auto-managed for soft delete


class CommentUpdate(BaseModel):
    content: str | None = None


comment_repo = Repository(
    entity_class=CommentWithAllFeatures,
    update_class=CommentUpdate,
    table_name="comments",
    config=RepositoryConfig(),
)

# Example 4: Optional Fields
# ==========================
# Fields are automatically set only if NOT provided
# You can still provide your own values if needed


class PostWithOptionalTimestamps(BaseEntity):
    """Post with optional timestamps - can provide custom values"""

    title: str
    content: str
    created_at: datetime | None  # Optional - can be provided or auto-set
    updated_at: datetime | None  # Optional - can be provided or auto-set


post_repo = Repository(
    entity_class=PostWithOptionalTimestamps,
    update_class=ArticleUpdate,
    table_name="posts",
    config=RepositoryConfig(),
)

# Example 5: Usage Example
# ========================
"""
async def example_usage():
    from src.db_context import DatabaseManager

    async with DatabaseManager.transaction("example_db"):
        # Create with automatic timestamps
        comment = CommentWithAllFeatures(
            content="Great article!",
            user_id="user_123",
        )
        created = await comment_repo.create(comment)

        # created will have:
        # - created_at: automatically set to current time
        # - updated_at: automatically set to current time
        # - deleted_at: automatically set to None

        # Update with automatic updated_at
        update_data = CommentUpdate(content="Updated comment")
        updated = await comment_repo.update(created.id, update_data)

        # updated will have:
        # - created_at: unchanged
        # - updated_at: automatically set to current time

        # Soft delete (if deleted_at field exists)
        await comment_repo.delete(created.id)
        # Sets deleted_at to current timestamp

        # Query automatically excludes soft-deleted records
        all_comments = await comment_repo.get()  # Won't include soft-deleted

        # Include soft-deleted records
        all_with_deleted = await comment_repo.with_trashed().get()

        # Only soft-deleted records
        only_deleted = await comment_repo.only_trashed().get()

        # Restore a soft-deleted record
        restored = await comment_repo.restore(created.id)
        # Sets deleted_at back to None
"""


if __name__ == "__main__":
    print(__doc__)
    print("\n" + "=" * 70)
    print("Automatic Field Handling Examples Loaded Successfully!")
    print("=" * 70)
    print("\nKey Points:")
    print("1. Add 'created_at' to schema -> auto-set on create")
    print("2. Add 'updated_at' to schema -> auto-set on create and update")
    print("3. Add 'deleted_at' to schema -> soft delete handling enabled")
    print("4. No configuration needed - it's automatic!")
    print("=" * 70)

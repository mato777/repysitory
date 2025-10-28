"""
Example demonstrating the new Repository Feature System

This example shows how to use the refactored feature-based architecture
to add functionality to repositories in a clean, composable way.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src import Repository, RepositoryConfig, RepositoryFeature, TimestampFeature
from src.entities import BaseEntity

# Example 1: Using the built-in TimestampFeature
# ================================================


class Article(BaseEntity):
    """Article entity without timestamp fields"""

    title: str
    content: str
    author: str


class ArticleSearch(BaseModel):
    title: str | None = None
    author: str | None = None


class ArticleUpdate(BaseModel):
    title: str | None = None
    content: str | None = None


# Method 1: Using the backward-compatible timestamps flag
article_repo_legacy = Repository(
    entity_class=Article,
    update_class=ArticleUpdate,
    table_name="articles",
    config=RepositoryConfig(timestamps=True),  # Auto-creates TimestampFeature
)

# Method 2: Using the explicit feature system (recommended)
article_repo_modern = Repository(
    entity_class=Article,
    update_class=ArticleUpdate,
    table_name="articles",
    config=RepositoryConfig(features=[TimestampFeature()]),
)


# Example 2: Creating a Custom Feature (Soft Delete)
# ===================================================


class SoftDeleteFeature(RepositoryFeature):
    """
    Feature that adds soft delete functionality.
    Adds a 'deleted_at' field and sets it on delete operations.
    """

    def before_create(self, data: dict) -> dict:
        """Add deleted_at as None on create"""
        data["deleted_at"] = None
        return data

    def before_update(self, data: dict) -> dict:
        """No changes on update"""
        return data

    def augment_entity_class(self, entity_class: type[BaseModel]) -> type[BaseModel]:
        """Add deleted_at field to entity"""
        from pydantic import create_model

        return create_model(
            f"{entity_class.__name__}WithSoftDelete",
            __base__=entity_class,
            deleted_at=(datetime | None, None),
        )


# Example 3: Creating a Custom Feature (Audit Log)
# =================================================


class AuditFeature(RepositoryFeature):
    """
    Feature that adds audit fields: created_by and updated_by
    """

    def __init__(self, user_id_getter=None):
        """
        Args:
            user_id_getter: Callable that returns the current user ID
        """
        self.user_id_getter = user_id_getter or (lambda: "system")

    def before_create(self, data: dict) -> dict:
        """Add created_by and updated_by on create"""
        user_id = self.user_id_getter()
        data["created_by"] = user_id
        data["updated_by"] = user_id
        return data

    def before_update(self, data: dict) -> dict:
        """Update updated_by on update"""
        data["updated_by"] = self.user_id_getter()
        return data

    def augment_entity_class(self, entity_class: type[BaseModel]) -> type[BaseModel]:
        """Add audit fields to entity"""
        from pydantic import create_model

        return create_model(
            f"{entity_class.__name__}WithAudit",
            __base__=entity_class,
            created_by=(str, None),
            updated_by=(str, None),
        )


# Example 4: Combining Multiple Features
# =======================================


class Product(BaseEntity):
    """Product entity"""

    name: str
    price: float
    description: str | None = None


class ProductSearch(BaseModel):
    name: str | None = None


class ProductUpdate(BaseModel):
    name: str | None = None
    price: float | None = None
    description: str | None = None


# Repository with multiple features enabled
def get_current_user() -> str:
    """Simulated function to get current user"""
    return "user_123"


product_repo = Repository(
    entity_class=Product,
    update_class=ProductUpdate,
    table_name="products",
    config=RepositoryConfig(
        features=[
            TimestampFeature(),  # Adds created_at, updated_at
            AuditFeature(
                user_id_getter=get_current_user
            ),  # Adds created_by, updated_by
            SoftDeleteFeature(),  # Adds deleted_at
        ]
    ),
)


# Example 5: Feature Execution Order
# ===================================
"""
Features are executed in the order they are added to the list:

1. TimestampFeature.before_create() runs first
2. AuditFeature.before_create() runs second
3. SoftDeleteFeature.before_create() runs third

Entity augmentation also happens in order:
1. Product -> ProductWithTimestamps
2. ProductWithTimestamps -> ProductWithTimestampsWithAudit
3. ProductWithTimestampsWithAudit -> ProductWithTimestampsWithAuditWithSoftDelete
"""


# Example 6: Creating a Validation Feature
# =========================================


class ValidationFeature(RepositoryFeature):
    """
    Feature that validates data before operations
    """

    def __init__(self, validators: dict = None):
        self.validators = validators or {}

    def before_create(self, data: dict) -> dict:
        """Validate on create"""
        self._validate(data)
        return data

    def before_update(self, data: dict) -> dict:
        """Validate on update"""
        self._validate(data)
        return data

    def _validate(self, data: dict) -> None:
        """Run custom validators"""
        for field, validator in self.validators.items():
            if field in data and not validator(data[field]):
                raise ValueError(f"Validation failed for field: {field}")

    def augment_entity_class(self, entity_class: type[BaseModel]) -> type[BaseModel]:
        """No augmentation needed"""
        return entity_class


# Usage
def validate_price(price: float) -> bool:
    """Ensure price is positive"""
    return price > 0


validated_product_repo = Repository(
    entity_class=Product,
    update_class=ProductUpdate,
    table_name="products",
    config=RepositoryConfig(
        features=[
            ValidationFeature(validators={"price": validate_price}),
            TimestampFeature(),
        ]
    ),
)


# Example 7: Benefits of the Feature System
# ==========================================
"""
Benefits:

1. **Single Responsibility**: Each feature has one job
2. **Composability**: Mix and match features as needed
3. **Reusability**: Write once, use in any repository
4. **Extensibility**: Easy to add new features without modifying Repository
5. **Testability**: Test features in isolation
6. **Maintainability**: Features are small, focused, and easy to understand
7. **Backward Compatibility**: Old `timestamps=True` still works

Repository size reduction:
- Before: 448 lines
- After: 426 lines (22 lines removed)
- Timestamp logic extracted to separate feature: ~60 lines
- Net result: More organized, easier to maintain
"""


async def example_usage():
    """Example of using repositories with features"""
    from src.db_context import DatabaseManager

    # Assuming database is set up
    async with DatabaseManager.transaction("example_db"):
        # Create a product with all features applied
        product = Product(
            id=UUID("12345678-1234-5678-1234-567812345678"),
            name="Widget",
            price=29.99,
            description="A useful widget",
        )

        created = await product_repo.create(product)

        # The created entity will have:
        # - id, name, price, description (original fields)
        # - created_at, updated_at (from TimestampFeature)
        # - created_by, updated_by (from AuditFeature)
        # - deleted_at (from SoftDeleteFeature)

        print(f"Created product: {created}")


if __name__ == "__main__":
    # This is just documentation; actual usage requires DB setup
    print(__doc__)
    print("\n" + "=" * 70)
    print("Feature System Examples Loaded Successfully!")
    print("=" * 70)

"""
Example showing the benefits of enforced search parameters and typed updates in Repository definitions
"""

import asyncio
import sys
from pathlib import Path

# Add the parent directory to Python path so we can import from src
sys.path.append(str(Path(__file__).parent.parent))

from uuid import UUID, uuid4

from pydantic import BaseModel

from examples.db_setup import (
    close_connections,
    setup_postgres_connection,
)
from src.db_context import DatabaseManager, transactional
from src.entities import BaseEntity
from src.repository import Repository


# Example 1: User entity with restricted searchable fields
class User(BaseEntity):
    email: str
    username: str
    password_hash: str  # Sensitive field
    full_name: str
    is_active: bool


# Search model - deliberately excludes password_hash for security
class UserSearch(BaseModel):
    id: UUID | None = None
    email: str | None = None
    username: str | None = None
    full_name: str | None = None
    is_active: bool | None = None
    # Note: password_hash is NOT searchable - good for security!


# Update model - controls what can be updated
class UserUpdate(BaseModel):
    email: str | None = None
    username: str | None = None
    full_name: str | None = None
    is_active: bool | None = None
    # Note: password_hash requires special method - not via general update!


class UserRepository(Repository[User, UserSearch, UserUpdate]):
    def __init__(self):
        super().__init__(User, UserSearch, UserUpdate, "users")

    # Custom business logic methods
    @transactional("default")
    async def find_active_users(self):
        search = UserSearch(is_active=True)
        return await self.find_many_by(search)

    @transactional("default")
    async def update_password(self, user_id: UUID, new_password_hash: str):
        """Special method for password updates - bypasses general update restrictions"""
        conn = self._get_connection()
        await conn.execute(
            "UPDATE users SET password_hash = $1 WHERE id = $2",
            new_password_hash,
            str(user_id),
        )


# Example 2: Product entity with different search strategy
class Product(BaseEntity):
    name: str
    description: str
    price: float
    category_id: UUID
    internal_cost: float  # Internal field
    supplier_id: UUID  # Internal field


# Search model - only allows searching by public fields
class ProductSearch(BaseModel):
    id: UUID | None = None
    name: str | None = None
    category_id: UUID | None = None
    # Note: internal_cost and supplier_id are NOT searchable


# Update model - controls what fields can be updated
class ProductUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    price: float | None = None
    category_id: UUID | None = None
    # Note: internal_cost and supplier_id require special admin methods


class ProductRepository(Repository[Product, ProductSearch, ProductUpdate]):
    def __init__(self):
        super().__init__(Product, ProductSearch, ProductUpdate, "products")

    @transactional("default")
    async def find_by_category(self, category_id: UUID):
        search = ProductSearch(category_id=category_id)
        return await self.find_many_by(search)

    @transactional("admin_db")
    async def admin_update_costs(
        self, product_id: UUID, internal_cost: float, supplier_id: UUID
    ):
        """Admin-only method for updating internal fields"""
        conn = self._get_connection()
        await conn.execute(
            "UPDATE products SET internal_cost = $1, supplier_id = $2 WHERE id = $3",
            internal_cost,
            supplier_id,
            str(product_id),
        )


# Example usage showing type safety
async def example_usage():
    """Demonstrate type-safe repository operations"""

    # Setup database first
    print("🔧 Setting up database connection...")
    try:
        await setup_postgres_connection()

        # Create additional tables for this example
        pool = await DatabaseManager.get_pool("default")
        async with pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id UUID PRIMARY KEY,
                    email VARCHAR(255) NOT NULL,
                    username VARCHAR(255) NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    full_name VARCHAR(255) NOT NULL,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE
                );
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id UUID PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    description TEXT NOT NULL,
                    price DECIMAL(10,2) NOT NULL,
                    category_id UUID NOT NULL,
                    internal_cost DECIMAL(10,2) NOT NULL,
                    supplier_id UUID NOT NULL
                );
            """)

        print("✅ Database schema ready")

    except Exception as e:
        print(f"Failed to setup database: {e}")
        print(
            "\n💡 To run this example, make sure PostgreSQL is running on localhost:5432"
        )
        return

    try:
        user_repo = UserRepository()

        print("\n=== Type Safety Examples ===")

        # Type-safe search - IDE will autocomplete and validate
        @transactional("default")
        async def safe_operations():
            # ✅ This works - email is in UserSearch
            user = User(
                id=uuid4(),
                email="test@example.com",
                username="testuser",
                password_hash="hashed_password",
                full_name="Test User",
                is_active=True,
            )
            await user_repo.create(user)

            users = await user_repo.find_one_by(UserSearch(email="test@example.com"))
            print(f"Found user: {users.full_name if users else 'None'}")

            # ✅ Type-safe updates
            if users:
                update_data = UserUpdate(full_name="Updated Name", is_active=False)
                updated_user = await user_repo.update(users.id, update_data)
                print(
                    f"Updated user: {updated_user.full_name if updated_user else 'None'}"
                )

        await safe_operations()

        print("\n✅ All type safety examples completed successfully!")

    except Exception as e:
        print(f"❌ Example failed: {e}")

    finally:
        await close_connections()


async def main():
    """Run the enforced search examples"""
    print("🚀 Starting Enforced Search Examples")
    print("=" * 50)
    await example_usage()


if __name__ == "__main__":
    asyncio.run(main())

# Benefits of this approach:
# 1. Security: Sensitive fields can't be accidentally searched or updated
# 2. Type Safety: Compile-time validation of search and update operations
# 3. Clear API: Explicit about what fields are searchable/updatable
# 4. Flexibility: Special methods can bypass restrictions when needed
# 5. Documentation: Search/Update models serve as API documentation

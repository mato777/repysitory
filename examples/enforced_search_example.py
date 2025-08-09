"""
Example showing the benefits of enforced search parameters and typed updates in Repository definitions
"""
from pydantic import BaseModel
from uuid import UUID, uuid4
from typing import Optional
from src.repository import Repository
from src.entities import BaseEntity
from src.db_context import transactional

# Example 1: User entity with restricted searchable fields
class User(BaseEntity):
    email: str
    username: str
    password_hash: str  # Sensitive field
    full_name: str
    is_active: bool

# Search model - deliberately excludes password_hash for security
class UserSearch(BaseModel):
    id: Optional[UUID] = None
    email: Optional[str] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    # Note: password_hash is NOT searchable - good for security!

# Update model - controls what can be updated
class UserUpdate(BaseModel):
    email: Optional[str] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
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
            new_password_hash, str(user_id)
        )

# Example 2: Product entity with different search strategy
class Product(BaseEntity):
    name: str
    description: str
    price: float
    category_id: UUID
    internal_cost: float  # Internal field
    supplier_id: UUID     # Internal field

# Search model - only allows searching by public fields
class ProductSearch(BaseModel):
    id: Optional[UUID] = None
    name: Optional[str] = None
    category_id: Optional[UUID] = None
    # Note: internal_cost and supplier_id are NOT searchable

# Update model - controls what fields can be updated
class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    category_id: Optional[UUID] = None
    # Note: internal_cost and supplier_id require special admin methods

class ProductRepository(Repository[Product, ProductSearch, ProductUpdate]):
    def __init__(self):
        super().__init__(Product, ProductSearch, ProductUpdate, "products")

    @transactional("default")
    async def find_by_category(self, category_id: UUID):
        search = ProductSearch(category_id=category_id)
        return await self.find_many_by(search)

    @transactional("admin_db")
    async def admin_update_costs(self, product_id: UUID, internal_cost: float, supplier_id: UUID):
        """Admin-only method for updating internal fields"""
        conn = self._get_connection()
        await conn.execute(
            "UPDATE products SET internal_cost = $1, supplier_id = $2 WHERE id = $3",
            internal_cost, supplier_id, str(product_id)
        )

# Example usage showing type safety
async def example_usage():
    user_repo = UserRepository()
    product_repo = ProductRepository()

    # Type-safe search - IDE will autocomplete and validate
    @transactional("default")
    async def safe_operations():
        # ✅ This works - email is in UserSearch
        users = await user_repo.find_one_by(UserSearch(email="test@example.com"))

        # ❌ This would be a compile error - password_hash not in UserSearch
        # users = await user_repo.find_one_by(UserSearch(password_hash="secret"))

        # ✅ Type-safe updates
        if users:
            update_data = UserUpdate(full_name="Updated Name", is_active=False)
            await user_repo.update(users.id, update_data)

            # ❌ This would be a compile error - password_hash not in UserUpdate
            # await user_repo.update(users.id, UserUpdate(password_hash="new_hash"))

# Benefits of this approach:
# 1. Security: Sensitive fields can't be accidentally searched or updated
# 2. Type Safety: Compile-time validation of search and update operations
# 3. Clear API: Explicit about what fields are searchable/updatable
# 4. Flexibility: Special methods can bypass restrictions when needed
# 5. Documentation: Search/Update models serve as API documentation

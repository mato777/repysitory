"""
Example showing the benefits of enforced search parameters in Repository definitions
"""
from pydantic import BaseModel
from uuid import UUID, uuid4
from typing import Optional
from repository import Repository

# Example 1: User entity with restricted searchable fields
class User(BaseModel):
    id: UUID = uuid4()
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

class UserRepository(Repository[User, UserSearch]):
    def __init__(self, db_name: str = "default"):
        super().__init__(User, UserSearch, "users", db_name)

    # Custom business logic methods
    async def find_active_users(self):
        search = UserSearch(is_active=True)
        return await self.find_many_by(search)


# Example 2: Product entity with different search strategy
class Product(BaseModel):
    id: UUID = uuid4()
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

class ProductRepository(Repository[Product, ProductSearch]):
    def __init__(self, db_name: str = "default"):
        super().__init__(Product, ProductSearch, "products", db_name)


# Example 3: Admin-only repository with full search capabilities
class ProductAdminSearch(BaseModel):
    id: Optional[UUID] = None
    name: Optional[str] = None
    category_id: Optional[UUID] = None
    internal_cost: Optional[float] = None  # Admin can search by internal fields
    supplier_id: Optional[UUID] = None

class ProductAdminRepository(Repository[Product, ProductAdminSearch]):
    def __init__(self, db_name: str = "default"):
        super().__init__(Product, ProductAdminSearch, "products", db_name)


async def example_usage():
    """Examples showing type safety and field restrictions"""

    # User repository - password_hash is not searchable
    user_repo = UserRepository()

    # ✅ This works - searching by allowed fields
    search = UserSearch(email="user@example.com", is_active=True)
    user = await user_repo.find_one_by(search)

    # ❌ This would cause a type error - password_hash is not in UserSearch
    # search = UserSearch(password_hash="some_hash")  # IDE error!

    # Product repository - internal fields not searchable
    product_repo = ProductRepository()

    # ✅ This works - searching by public fields
    search = ProductSearch(name="iPhone", category_id=some_uuid)
    products = await product_repo.find_many_by(search)

    # ❌ This would cause a type error - internal_cost not in ProductSearch
    # search = ProductSearch(internal_cost=100.0)  # IDE error!

    # Admin repository - can search by internal fields
    admin_repo = ProductAdminRepository()

    # ✅ This works - admin can search by internal fields
    search = ProductAdminSearch(internal_cost=100.0, supplier_id=supplier_uuid)
    products = await admin_repo.find_many_by(search)


if __name__ == "__main__":
    import asyncio
    asyncio.run(example_usage())

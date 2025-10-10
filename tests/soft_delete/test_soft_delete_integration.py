"""
Integration tests for SoftDeleteFeature with actual database operations

These tests verify that soft delete works correctly with real database operations.
"""

from datetime import datetime
from uuid import uuid4

import pytest
import pytest_asyncio
from pydantic import BaseModel

from src.db_context import DatabaseManager
from src.entities import BaseEntity
from src.features.soft_delete_feature import SoftDeleteFeature
from src.features.timestamp_feature import TimestampFeature
from src.repository import Repository, RepositoryConfig


class Product(BaseEntity):
    """Product entity for soft delete testing"""

    name: str
    price: float
    category: str | None = None


class ProductSearch(BaseModel):
    """Search model for products"""

    name: str | None = None
    category: str | None = None
    deleted_at: datetime | None = None


class ProductUpdate(BaseModel):
    """Update model for products"""

    name: str | None = None
    price: float | None = None
    category: str | None = None
    deleted_at: datetime | None = None


@pytest_asyncio.fixture
async def setup_soft_delete_table(test_db_pool):
    """Setup table with deleted_at column for soft delete testing"""
    async with test_db_pool.acquire() as conn:
        await conn.execute("DROP TABLE IF EXISTS products CASCADE")
        await conn.execute(
            """
            CREATE TABLE products (
                id UUID PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                price DECIMAL(10, 2) NOT NULL,
                category VARCHAR(100),
                deleted_at TIMESTAMP WITH TIME ZONE
            )
        """
        )
    yield
    async with test_db_pool.acquire() as conn:
        await conn.execute("DROP TABLE IF EXISTS products CASCADE")


@pytest_asyncio.fixture
async def setup_soft_delete_with_timestamps_table(test_db_pool):
    """Setup table with both timestamps and soft delete"""
    async with test_db_pool.acquire() as conn:
        await conn.execute("DROP TABLE IF EXISTS products CASCADE")
        await conn.execute(
            """
            CREATE TABLE products (
                id UUID PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                price DECIMAL(10, 2) NOT NULL,
                category VARCHAR(100),
                created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
                deleted_at TIMESTAMP WITH TIME ZONE
            )
        """
        )
    yield
    async with test_db_pool.acquire() as conn:
        await conn.execute("DROP TABLE IF EXISTS products CASCADE")


@pytest.fixture
def product_repo_with_soft_delete():
    """Repository with soft delete enabled"""
    return Repository(
        entity_class=Product,
        search_class=ProductSearch,
        update_class=ProductUpdate,
        table_name="products",
        config=RepositoryConfig(features=[SoftDeleteFeature()]),
    )


@pytest.fixture
def product_repo_with_all_features():
    """Repository with both timestamps and soft delete"""
    return Repository(
        entity_class=Product,
        search_class=ProductSearch,
        update_class=ProductUpdate,
        table_name="products",
        config=RepositoryConfig(features=[TimestampFeature(), SoftDeleteFeature()]),
    )


@pytest.mark.asyncio
class TestSoftDeleteIntegration:
    """Integration tests for soft delete functionality"""

    async def test_create_with_soft_delete(
        self, setup_soft_delete_table, product_repo_with_soft_delete
    ):
        """Test creating an entity with soft delete feature"""
        async with DatabaseManager.transaction("test_db"):
            product = Product(
                id=uuid4(),
                name="Widget",
                price=29.99,
                category="Electronics",
            )

            created = await product_repo_with_soft_delete.create(product)

            assert created.deleted_at is None
            assert created.name == "Widget"
            assert created.price == 29.99

    async def test_find_by_id_with_soft_delete(
        self, setup_soft_delete_table, product_repo_with_soft_delete
    ):
        """Test finding an entity with soft delete field"""
        async with DatabaseManager.transaction("test_db"):
            product_id = uuid4()
            product = Product(
                id=product_id,
                name="Gadget",
                price=49.99,
            )

            await product_repo_with_soft_delete.create(product)
            found = await product_repo_with_soft_delete.find_by_id(product_id)

            assert found is not None
            assert found.deleted_at is None
            assert found.name == "Gadget"

    async def test_soft_delete_via_delete(
        self, setup_soft_delete_table, product_repo_with_soft_delete
    ):
        """Test soft deleting an entity using repo.delete()"""
        async with DatabaseManager.transaction("test_db"):
            product_id = uuid4()
            product = Product(
                id=product_id,
                name="Item to Delete",
                price=19.99,
            )

            # Create the product
            await product_repo_with_soft_delete.create(product)

            # Soft delete using delete() method
            result = await product_repo_with_soft_delete.delete(product_id)
            assert result is True

            # Verify it was soft deleted (need to use with_trashed to find it)
            deleted = await product_repo_with_soft_delete.with_trashed().find_by_id(
                product_id
            )

            assert deleted is not None
            assert deleted.deleted_at is not None
            assert isinstance(deleted.deleted_at, datetime)
            assert deleted.name == "Item to Delete"  # Other fields unchanged

    async def test_restore_soft_deleted_entity(
        self, setup_soft_delete_table, product_repo_with_soft_delete
    ):
        """Test restoring a soft-deleted entity"""
        async with DatabaseManager.transaction("test_db"):
            product_id = uuid4()
            product = Product(
                id=product_id,
                name="Item to Restore",
                price=39.99,
            )

            # Create and soft delete
            await product_repo_with_soft_delete.create(product)
            await product_repo_with_soft_delete.delete(product_id)

            # Restore using restore() method
            restored = await product_repo_with_soft_delete.restore(product_id)

            assert restored is not None
            assert restored.deleted_at is None
            assert restored.name == "Item to Restore"

    async def test_find_only_non_deleted_with_query_builder(
        self, setup_soft_delete_table, product_repo_with_soft_delete
    ):
        """Test that get() automatically excludes soft-deleted entities"""
        async with DatabaseManager.transaction("test_db"):
            # Create active products
            product1 = Product(id=uuid4(), name="Active 1", price=10.00)
            product2 = Product(id=uuid4(), name="Active 2", price=20.00)

            # Create product to be deleted
            product3 = Product(id=uuid4(), name="Deleted 1", price=30.00)

            await product_repo_with_soft_delete.create(product1)
            await product_repo_with_soft_delete.create(product2)
            created3 = await product_repo_with_soft_delete.create(product3)

            # Soft delete product3 using delete()
            await product_repo_with_soft_delete.delete(created3.id)

            # Query for non-deleted products (should auto-exclude soft deleted)
            active_products = await product_repo_with_soft_delete.get()

            assert len(active_products) == 2
            names = [p.name for p in active_products]
            assert "Active 1" in names
            assert "Active 2" in names
            assert "Deleted 1" not in names

    async def test_find_only_deleted_products(
        self, setup_soft_delete_table, product_repo_with_soft_delete
    ):
        """Test finding only soft-deleted entities using only_trashed()"""
        async with DatabaseManager.transaction("test_db"):
            # Create and keep active
            product1 = Product(id=uuid4(), name="Active", price=10.00)
            await product_repo_with_soft_delete.create(product1)

            # Create and soft delete
            product2 = Product(id=uuid4(), name="Deleted", price=20.00)
            created2 = await product_repo_with_soft_delete.create(product2)
            await product_repo_with_soft_delete.delete(created2.id)

            # Query for deleted products using only_trashed()
            deleted_products = await product_repo_with_soft_delete.only_trashed().get()

            assert len(deleted_products) == 1
            assert deleted_products[0].name == "Deleted"
            assert deleted_products[0].deleted_at is not None

    async def test_combined_timestamps_and_soft_delete(
        self, setup_soft_delete_with_timestamps_table, product_repo_with_all_features
    ):
        """Test using both timestamps and soft delete features together"""
        async with DatabaseManager.transaction("test_db"):
            product_id = uuid4()
            product = Product(
                id=product_id,
                name="Full Featured",
                price=99.99,
            )

            # Create
            created = await product_repo_with_all_features.create(product)

            assert created.created_at is not None
            assert created.updated_at is not None
            assert created.deleted_at is None

            # Update (should change updated_at but not deleted_at)
            update_data = ProductUpdate(price=89.99)
            updated = await product_repo_with_all_features.update(
                product_id, update_data
            )

            assert updated.created_at == created.created_at
            assert updated.updated_at > created.updated_at
            assert updated.deleted_at is None

            # Soft delete using delete() (should set deleted_at)
            await product_repo_with_all_features.delete(product_id)

            deleted = await product_repo_with_all_features.with_trashed().find_by_id(
                product_id
            )

            assert deleted.created_at == created.created_at
            assert deleted.updated_at == updated.updated_at
            assert deleted.deleted_at is not None

    async def test_create_many_with_soft_delete(
        self, setup_soft_delete_table, product_repo_with_soft_delete
    ):
        """Test bulk create with soft delete feature"""
        async with DatabaseManager.transaction("test_db"):
            products = [
                Product(id=uuid4(), name=f"Product {i}", price=float(i * 10))
                for i in range(1, 4)
            ]

            created = await product_repo_with_soft_delete.create_many(products)

            assert len(created) == 3
            for product in created:
                assert product.deleted_at is None

    async def test_bulk_soft_delete(
        self, setup_soft_delete_table, product_repo_with_soft_delete
    ):
        """Test bulk soft delete using where().delete()"""
        async with DatabaseManager.transaction("test_db"):
            # Create multiple products
            products = [
                Product(id=uuid4(), name=f"Product {i}", price=float(i * 10))
                for i in range(1, 4)
            ]
            created = await product_repo_with_soft_delete.create_many(products)
            ids = [p.id for p in created]

            # Soft delete all using where().delete()
            deleted_count = await product_repo_with_soft_delete.where_in(
                "id", [str(id) for id in ids]
            ).delete()

            assert deleted_count == 3

            # Verify they are soft deleted
            trashed = await product_repo_with_soft_delete.only_trashed().get()
            assert len(trashed) == 3
            for product in trashed:
                assert product.deleted_at is not None

    async def test_soft_delete_with_search_criteria(
        self, setup_soft_delete_table, product_repo_with_soft_delete
    ):
        """Test searching with category - soft deleted are auto-excluded"""
        async with DatabaseManager.transaction("test_db"):
            # Create active product
            product1 = Product(
                id=uuid4(), name="Active Product", price=50.00, category="Electronics"
            )
            await product_repo_with_soft_delete.create(product1)

            # Create and soft delete product
            product2 = Product(
                id=uuid4(), name="Deleted Product", price=60.00, category="Electronics"
            )
            created2 = await product_repo_with_soft_delete.create(product2)
            await product_repo_with_soft_delete.delete(created2.id)

            # Search for electronics - should only find active ones
            search = ProductSearch(category="Electronics")
            results = await product_repo_with_soft_delete.find_many_by(search)

            assert len(results) == 1
            assert results[0].name == "Active Product"

    async def test_deleted_at_timestamp_format(
        self, setup_soft_delete_table, product_repo_with_soft_delete
    ):
        """Test that deleted_at is stored as proper timestamp"""
        async with DatabaseManager.transaction("test_db"):
            product_id = uuid4()
            product = Product(id=product_id, name="Test", price=10.00)

            await product_repo_with_soft_delete.create(product)

            # Soft delete using delete()
            await product_repo_with_soft_delete.delete(product_id)

            # Verify we can find it with with_trashed() and check timestamp
            deleted = await product_repo_with_soft_delete.with_trashed().find_by_id(
                product_id
            )

            assert deleted is not None
            assert isinstance(deleted.deleted_at, datetime)
            assert deleted.deleted_at.tzinfo is not None  # Has timezone info

            # Verify it's not found without with_trashed()
            found = await product_repo_with_soft_delete.find_by_id(product_id)
            assert found is None

    async def test_count_with_soft_delete_filter(
        self, setup_soft_delete_table, product_repo_with_soft_delete
    ):
        """Test counting with automatic soft delete filtering"""
        async with DatabaseManager.transaction("test_db"):
            # Create 5 products
            products = [
                Product(id=uuid4(), name=f"Product {i}", price=float(i * 10))
                for i in range(1, 6)
            ]
            created = await product_repo_with_soft_delete.create_many(products)

            # Soft delete 2 of them using delete()
            await product_repo_with_soft_delete.delete(created[0].id)
            await product_repo_with_soft_delete.delete(created[1].id)

            # Count active products (default excludes soft-deleted)
            active_count = await product_repo_with_soft_delete.count()
            assert active_count == 3

            # Count deleted products using only_trashed()
            deleted_count = await product_repo_with_soft_delete.only_trashed().count()
            assert deleted_count == 2

            # Count all products using with_trashed()
            total_count = await product_repo_with_soft_delete.with_trashed().count()
            assert total_count == 5

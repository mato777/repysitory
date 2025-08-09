import pytest
import pytest_asyncio
from src.db_context import DatabaseManager


class TestDatabaseManager:
    """Test DatabaseManager functionality"""

    @pytest.mark.asyncio
    async def test_get_pool_not_found(self):
        """Test that get_pool raises ValueError when pool doesn't exist"""
        with pytest.raises(ValueError, match="Database pool 'nonexistent' not found"):
            await DatabaseManager.get_pool("nonexistent")

    @pytest.mark.asyncio
    async def test_get_current_connection_no_context(self):
        """Test that get_current_connection returns None when no transaction context"""
        connection = DatabaseManager.get_current_connection()
        assert connection is None

    @pytest.mark.asyncio
    async def test_add_and_get_pool(self, postgres_container):
        """Test adding and retrieving a database pool"""
        import asyncpg

        # Get connection details from the container
        host = postgres_container.get_container_host_ip()
        port = postgres_container.get_exposed_port(5432)
        dsn = f"postgresql://{postgres_container.username}:{postgres_container.password}@{host}:{port}/{postgres_container.dbname}"

        # Create a test pool
        pool = await asyncpg.create_pool(dsn, min_size=1, max_size=3)

        try:
            # Add pool to DatabaseManager
            await DatabaseManager.add_pool("test_pool", pool)

            # Retrieve the pool
            retrieved_pool = await DatabaseManager.get_pool("test_pool")
            assert retrieved_pool is pool

        finally:
            await pool.close()

import asyncpg
import pytest_asyncio
from testcontainers.postgres import PostgresContainer

from src.db_context import DatabaseManager


@pytest_asyncio.fixture(scope="session")
async def postgres_container():
    """Start a PostgreSQL test container for the session."""
    with PostgresContainer("postgres:17") as postgres:
        yield postgres


@pytest_asyncio.fixture(autouse=True)
async def test_db_pool(postgres_container):
    """Create a database pool connected to the test container for each test."""
    # Get connection details from the container
    host = postgres_container.get_container_host_ip()
    port = postgres_container.get_exposed_port(5432)
    dsn = f"postgresql://{postgres_container.username}:{postgres_container.password}@{host}:{port}/{postgres_container.dbname}"

    # Create a new pool for each test to avoid event loop issues
    pool = await asyncpg.create_pool(dsn, min_size=1, max_size=5)

    # Initialize the database schema
    async with pool.acquire() as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS posts (
                id UUID PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                content TEXT NOT NULL
            );
        """
        )

    # Add pool to DatabaseManager
    await DatabaseManager.add_pool("test", pool)

    yield pool

    async with pool.acquire() as conn:
        await conn.execute("TRUNCATE TABLE posts;")

    # Cleanup: close the pool after each test
    await pool.close()



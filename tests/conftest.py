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
                content TEXT NOT NULL,
                published BOOLEAN NOT NULL DEFAULT FALSE,
                category VARCHAR(100),
                author_id UUID
            );
        """
        )
        # Create test_posts table for type safe fields tests
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS test_posts (
                id UUID PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                content TEXT NOT NULL,
                published BOOLEAN NOT NULL DEFAULT FALSE,
                category VARCHAR(100),
                author_id UUID
            );
        """
        )
        # Ensure schema-qualified table exists for schema tests
        await conn.execute(
            """
            CREATE SCHEMA IF NOT EXISTS app;
            CREATE TABLE IF NOT EXISTS app.posts (
                id UUID PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                content TEXT NOT NULL,
                published BOOLEAN NOT NULL DEFAULT FALSE,
                category VARCHAR(100),
                author_id UUID
            );
        """
        )

    # Add pool to DatabaseManager
    await DatabaseManager.add_pool("test_db", pool)

    yield pool

    async with pool.acquire() as conn:
        await conn.execute("TRUNCATE TABLE posts;")
        await conn.execute("TRUNCATE TABLE test_posts;")
        await conn.execute("TRUNCATE TABLE app.posts;")

    # Cleanup: close the pool after each test
    await pool.close()

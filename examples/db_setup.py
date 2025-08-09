"""
Database setup utilities for examples
"""
import asyncpg
import sys
from pathlib import Path

# Add the parent directory to Python path so we can import from src
sys.path.append(str(Path(__file__).parent.parent))

from src.db_context import DatabaseManager

async def setup_postgres_connection(
    host: str = "localhost",
    port: int = 5432,
    database: str = "postgres",
    user: str = "root",
    password: str = "root",
    pool_name: str = "default"
):
    """
    Set up a connection pool to a local PostgreSQL instance.

    Default connection parameters:
    - Host: localhost
    - Port: 5432
    - Database: postgres
    - User: postgres
    - Password: postgres

    Make sure you have PostgreSQL running locally with these credentials,
    or modify the parameters to match your setup.
    """
    try:
        # Create connection pool
        pool = await asyncpg.create_pool(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
            min_size=1,
            max_size=10
        )

        # Add pool to DatabaseManager
        await DatabaseManager.add_pool(pool_name, pool)

        print(f"✅ Connected to PostgreSQL at {host}:{port}/{database} as {user}")
        return pool

    except Exception as e:
        print(f"❌ Failed to connect to PostgreSQL: {e}")
        print(f"Make sure PostgreSQL is running on {host}:{port}")
        print(f"And that database '{database}' exists with user '{user}'")
        raise

async def setup_example_schema(pool_name: str = "default"):
    """
    Create the posts table for examples if it doesn't exist.
    """
    try:
        pool = await DatabaseManager.get_pool(pool_name)
        async with pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS posts (
                    id UUID PRIMARY KEY,
                    title VARCHAR(255) NOT NULL,
                    content TEXT NOT NULL
                );
            """)
        print("✅ Posts table ready")
    except Exception as e:
        print(f"❌ Failed to create schema: {e}")
        raise

async def cleanup_example_data(pool_name: str = "default"):
    """
    Clean up example data (optional - for clean runs).
    """
    try:
        pool = await DatabaseManager.get_pool(pool_name)
        async with pool.acquire() as conn:
            await conn.execute("TRUNCATE TABLE posts;")
        print("🧹 Cleaned up existing posts")
    except Exception as e:
        print(f"⚠️  Could not clean up data: {e}")

async def close_connections():
    """
    Close all database connections (call this at the end of examples).
    """
    # You might want to implement a cleanup method in DatabaseManager
    print("🔒 Closing database connections")

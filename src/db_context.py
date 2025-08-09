import asyncpg
from contextvars import ContextVar
from typing import Dict, Optional
from contextlib import asynccontextmanager
from functools import wraps

# Context variable to store the current database connection (only one per context)
_current_connection: ContextVar[Optional[asyncpg.Connection]] = ContextVar('current_connection', default=None)
_db_pools: Dict[str, asyncpg.Pool] = {}

class DatabaseManager:
    """Manages database pools and connections"""

    @classmethod
    async def add_pool(cls, name: str, pool: asyncpg.Pool):
        """Add a database pool with a name"""
        _db_pools[name] = pool

    @classmethod
    async def get_pool(cls, name: str = "default") -> asyncpg.Pool:
        """Get a database pool by name"""
        if name not in _db_pools:
            raise ValueError(f"Database pool '{name}' not found")
        return _db_pools[name]

    @classmethod
    def get_current_connection(cls) -> Optional[asyncpg.Connection]:
        """Get the current active connection from context"""
        return _current_connection.get()

    @classmethod
    @asynccontextmanager
    async def transaction(cls, db_name: str = "default"):
        """Context manager for database transactions"""
        current_conn = _current_connection.get()

        # If connection already exists, use nested transaction
        if current_conn:
            async with current_conn.transaction():
                yield current_conn
        else:
            # Create new connection and transaction
            pool = await cls.get_pool(db_name)
            conn = await pool.acquire()
            try:
                async with conn.transaction():
                    token = _current_connection.set(conn)
                    try:
                        yield conn
                    finally:
                        _current_connection.reset(token)
            finally:
                await pool.release(conn)

def transactional(db_name: str = "default"):
    """Decorator to run function within a database transaction"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            async with DatabaseManager.transaction(db_name):
                return await func(*args, **kwargs)
        return wrapper
    return decorator

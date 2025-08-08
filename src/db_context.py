import asyncpg
from contextvars import ContextVar
from typing import Dict, Optional
from contextlib import asynccontextmanager
from functools import wraps

# Context variables to store database connections
_db_connections: ContextVar[Dict[str, asyncpg.Connection]] = ContextVar('db_connections', default={})
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
    def get_connection(cls, name: str = "default") -> Optional[asyncpg.Connection]:
        """Get current connection from context"""
        connections = _db_connections.get({})
        return connections.get(name)

    @classmethod
    @asynccontextmanager
    async def transaction(cls, db_name: str = "default"):
        """Context manager for database transactions"""
        pool = await cls.get_pool(db_name)
        current_connections = _db_connections.get({}).copy()

        # If connection already exists for this db, use nested transaction
        if db_name in current_connections:
            conn = current_connections[db_name]
            async with conn.transaction():
                yield conn
        else:
            # Create new connection and transaction
            async with pool.acquire() as conn:
                async with conn.transaction():
                    current_connections[db_name] = conn
                    token = _db_connections.set(current_connections)
                    try:
                        yield conn
                    finally:
                        _db_connections.reset(token)

def with_db(db_name: str = "default"):
    """Decorator to automatically provide database connection from context or create transaction"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Check if 'conn' is already provided in kwargs
            if 'conn' not in kwargs or kwargs['conn'] is None:
                conn = DatabaseManager.get_connection(db_name)
                if conn:
                    # Use existing connection from context
                    kwargs['conn'] = conn
                    return await func(*args, **kwargs)
                else:
                    # No existing connection, create a transaction for this operation
                    async with DatabaseManager.transaction(db_name) as transaction_conn:
                        kwargs['conn'] = transaction_conn
                        return await func(*args, **kwargs)
            else:
                # Connection already provided, use it directly
                return await func(*args, **kwargs)
        return wrapper
    return decorator

def transactional(db_name: str = "default"):
    """Decorator to run function within a database transaction"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            async with DatabaseManager.transaction(db_name) as conn:
                kwargs['conn'] = conn
                return await func(*args, **kwargs)
        return wrapper
    return decorator

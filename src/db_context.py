import traceback
from contextlib import asynccontextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import wraps
from typing import Any

import asyncpg

# Context variable to store the current database connection (only one per context)
_current_connection: ContextVar[asyncpg.Connection | None] = ContextVar(
    "current_connection", default=None
)
_db_pools: dict[str, asyncpg.Pool] = {}


@dataclass
class QueryLog:
    """Represents a logged query"""

    query: str
    params: list[Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    stack_trace: str | None = None

    def __repr__(self) -> str:
        return f"QueryLog(query={self.query!r}, params={self.params!r}, timestamp={self.timestamp}, stack_trace={self.stack_trace!r})"


class QueryTracker:
    """Tracks queries executed during a context"""

    def __init__(self):
        self.queries: list[QueryLog] = []
        self._enabled: bool = False

    def enable(self):
        """Enable query tracking"""
        self._enabled = True

    def disable(self):
        """Disable query tracking"""
        self._enabled = False

    def is_enabled(self) -> bool:
        """Check if query tracking is enabled"""
        return self._enabled

    def log_query(self, query: str, params: list[Any], stack_trace: str | None = None):
        """Log a query with its parameters and optional stack trace"""
        if self._enabled:
            self.queries.append(
                QueryLog(query=query, params=params, stack_trace=stack_trace)
            )

    def get_queries(self) -> list[QueryLog]:
        """Get all logged queries"""
        return self.queries.copy()

    def clear(self):
        """Clear all logged queries"""
        self.queries.clear()

    def count(self) -> int:
        """Get the number of logged queries"""
        return len(self.queries)

    def to_dict(self) -> list[dict[str, Any]]:
        """Convert logged queries to a list of dictionaries"""
        return [
            {
                "query": log.query,
                "params": log.params,
                "timestamp": log.timestamp.isoformat(),
                "stack_trace": log.stack_trace,
            }
            for log in self.queries
        ]


# Context variable to store the query tracker
_query_tracker: ContextVar[QueryTracker | None] = ContextVar(
    "query_tracker", default=None
)


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
    def get_current_connection(cls) -> asyncpg.Connection | None:
        """Get the current active connection from context"""
        return _current_connection.get()

    @classmethod
    def get_query_tracker(cls) -> QueryTracker | None:
        """Get the current query tracker from context"""
        return _query_tracker.get()

    @classmethod
    def log_query(cls, query: str, params: list[Any]):
        """Log a query to the current query tracker if available"""
        tracker = _query_tracker.get()
        if tracker:
            # Capture stack trace, skipping the current frame and the DatabaseOperations frame
            stack = traceback.extract_stack()
            # Skip the last 2 frames: this method and the DatabaseOperations method
            relevant_stack = stack[:-2]
            stack_trace = "".join(traceback.format_list(relevant_stack))
            tracker.log_query(query, params, stack_trace)

    @classmethod
    @asynccontextmanager
    async def transaction(cls, db_name: str = "default", track_queries: bool = False):
        """Context manager for database transactions.

        Behavior:
        - If called within an existing transaction/connection, it opens a nested transaction using the same connection.
        - Otherwise it acquires a connection from the asyncpg pool using `async with pool.acquire()` and starts a transaction.
        - The connection acquired from the pool is always released back to the pool when the context exits,
          regardless of whether it exits normally or due to an exception. This is guaranteed by the async
          context manager (`__aexit__`) of asyncpg's Pool.acquire.

        Args:
            db_name: Name of the database pool to use
            track_queries: Whether to enable query tracking for this transaction
        """
        current_conn = _current_connection.get()
        current_tracker = _query_tracker.get()

        # If a connection already exists, use nested transaction
        if current_conn:
            async with current_conn.transaction():
                yield current_conn
        else:
            # Create a new connection and transaction
            pool = await cls.get_pool(db_name)
            async with pool.acquire() as conn, conn.transaction():
                conn_token = _current_connection.set(conn)

                # Set up query tracker if requested and not already present
                tracker_token = None
                if track_queries and not current_tracker:
                    tracker = QueryTracker()
                    tracker.enable()
                    tracker_token = _query_tracker.set(tracker)

                try:
                    yield conn
                finally:
                    _current_connection.reset(conn_token)
                    if tracker_token:
                        _query_tracker.reset(tracker_token)

    @classmethod
    @asynccontextmanager
    async def track_queries(cls):
        """Context manager specifically for query tracking.

        Use this within a transaction to enable query tracking:

        async with DatabaseManager.transaction():
            async with DatabaseManager.track_queries() as tracker:
                # All queries here will be tracked
                await repo.find_by_id(some_id)
                queries = tracker.get_queries()
        """
        current_tracker = _query_tracker.get()

        if current_tracker:
            # Already have a tracker, just enable it
            was_enabled = current_tracker.is_enabled()
            current_tracker.enable()
            try:
                yield current_tracker
            finally:
                if not was_enabled:
                    current_tracker.disable()
        else:
            # Create a new tracker
            tracker = QueryTracker()
            tracker.enable()
            token = _query_tracker.set(tracker)
            try:
                yield tracker
            finally:
                _query_tracker.reset(token)


def transactional(db_name: str = "default", query_logs: bool = False):
    """Decorator to run a function within a database transaction.

    Args:
        db_name: Name of the database pool to use
        query_logs: Whether to enable query tracking for this transaction

    Example:
        @transactional(query_logs=True)
        async def create_user(user_data):
            user = await user_repo.create(user_data)
            tracker = Repository.get_query_tracker()
            if tracker:
                print(f"Executed {tracker.count()} queries")
            return user
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            async with DatabaseManager.transaction(db_name, track_queries=query_logs):
                return await func(*args, **kwargs)

        return wrapper

    return decorator

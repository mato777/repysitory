from typing import Any

import asyncpg

from src.db_context import DatabaseManager


class DatabaseOperations:
    """Composition class for database operations"""

    @staticmethod
    def get_connection() -> asyncpg.Connection:
        """Get the current database connection from context"""
        conn = DatabaseManager.get_current_connection()
        if not conn:
            raise ValueError(
                "No active transaction found. Repository methods must be called within a transaction context."
            )
        return conn

    async def fetch_all(self, query: str, params: list[Any]) -> list[Any]:
        """Execute query and fetch all rows"""
        conn = self.get_connection()
        DatabaseManager.log_query(query, params)
        return await conn.fetch(query, *params)

    async def fetch_one(self, query: str, params: list[Any]) -> Any:
        """Execute a query and fetch one row"""
        conn = self.get_connection()
        DatabaseManager.log_query(query, params)
        return await conn.fetchrow(query, *params)

    async def fetch_value(self, query: str, params: list[Any]) -> Any:
        """Execute query and fetch single value"""
        conn = self.get_connection()
        DatabaseManager.log_query(query, params)
        return await conn.fetchval(query, *params)

    async def execute_query(self, query: str, params: list[Any]) -> str:
        """Execute query and return result"""
        conn = self.get_connection()
        DatabaseManager.log_query(query, params)
        return await conn.execute(query, *params)

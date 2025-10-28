#!/usr/bin/env python3
"""Example demonstrating stack trace functionality in query tracking"""

import asyncio
from uuid import uuid4

from src.db_context import DatabaseManager
from src.repository import Repository
from tests.post_entities import Post, PostSearch, PostUpdate


async def example_function():
    """Example function that triggers database queries"""
    post_repo = Repository(Post, PostSearch, PostUpdate, "posts")
    test_id = uuid4()

    # This query will be tracked with stack trace
    result = await post_repo.find_by_id(test_id)
    return result


async def main():
    """Main function demonstrating stack trace capture"""
    async with (
        DatabaseManager.transaction("test_db"),
        DatabaseManager.track_queries() as tracker,
    ):
        # Call the example function
        await example_function()

        # Get the tracked queries
        queries = tracker.get_queries()

        print(f"Captured {len(queries)} queries with stack traces:")
        print("=" * 60)

        for i, query_log in enumerate(queries, 1):
            print(f"\nQuery {i}:")
            print(f"SQL: {query_log.query}")
            print(f"Params: {query_log.params}")
            print(f"Timestamp: {query_log.timestamp}")
            print("Stack Trace:")
            print(query_log.stack_trace)
            print("-" * 40)

        # Also demonstrate the to_dict method
        print("\nQuery data as dictionary:")
        queries_dict = tracker.to_dict()
        for i, query_dict in enumerate(queries_dict, 1):
            print(f"\nQuery {i} dict:")
            for key, value in query_dict.items():
                if key == "stack_trace":
                    print(f"  {key}: [Stack trace captured - {len(value)} characters]")
                else:
                    print(f"  {key}: {value}")


if __name__ == "__main__":
    asyncio.run(main())

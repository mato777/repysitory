"""
Query Tracking Example

This example demonstrates how to use the query tracking feature to monitor
all SQL queries executed within a transaction context.
"""

import asyncio
from uuid import uuid4

from examples.db_setup import get_pool
from src.db_context import DatabaseManager
from src.entities import User, UserSearch, UserUpdate
from src.repository import Repository


async def basic_query_tracking():
    """Basic example: Track queries in a transaction context"""
    print("\n=== Basic Query Tracking ===")

    user_repo = Repository(User, UserSearch, UserUpdate, "users")
    user_id = uuid4()

    # Method 1: Using track_queries context manager
    async with (
        DatabaseManager.transaction(),
        DatabaseManager.track_queries() as tracker,
    ):
        # Create a user
        new_user = User(id=user_id, name="Alice", email="alice@example.com")
        await user_repo.create(new_user)

        # Find the user
        _found_user = await user_repo.find_by_id(user_id)

        # Get all tracked queries
        queries = tracker.get_queries()
        print(f"\nTotal queries executed: {tracker.count()}")
        for i, query_log in enumerate(queries, 1):
            print(f"\nQuery {i}:")
            print(f"  SQL: {query_log.query}")
            print(f"  Params: {query_log.params}")
            print(f"  Timestamp: {query_log.timestamp}")


async def tracking_with_fluent_queries():
    """Track queries using fluent interface"""
    print("\n=== Tracking Fluent Queries ===")

    user_repo = Repository(User, UserSearch, UserUpdate, "users")

    async with (
        DatabaseManager.transaction(),
        DatabaseManager.track_queries() as tracker,
    ):
        # Complex query with fluent interface
        users = await (
            user_repo.where("name", "LIKE", "A%")
            .order_by_desc("created_at")
            .limit(10)
            .get()
        )

        print(f"\nFound {len(users)} users")
        print(f"Queries executed: {tracker.count()}")
        for query_log in tracker.get_queries():
            print(f"\nSQL: {query_log.query}")
            print(f"Params: {query_log.params}")


async def tracking_multiple_operations():
    """Track multiple repository operations"""
    print("\n=== Tracking Multiple Operations ===")

    user_repo = Repository(User, UserSearch, UserUpdate, "users")

    async with (
        DatabaseManager.transaction(),
        DatabaseManager.track_queries() as tracker,
    ):
        # Create multiple users
        users_to_create = [
            User(id=uuid4(), name=f"User {i}", email=f"user{i}@example.com")
            for i in range(3)
        ]
        await user_repo.create_many(users_to_create)

        # Find users
        all_users = await user_repo.where("name", "LIKE", "User%").get()

        # Count users
        count = await user_repo.where("name", "LIKE", "User%").count()

        print(f"\nTotal queries: {tracker.count()}")
        print(f"Users created: {len(users_to_create)}")
        print(f"Users found: {len(all_users)}")
        print(f"Count result: {count}")

        # Show all queries
        print("\nAll queries executed:")
        for i, query_log in enumerate(tracker.get_queries(), 1):
            print(f"\n{i}. {query_log.query[:80]}...")
            print(
                f"   Params: {query_log.params[:5]}..."
                if len(query_log.params) > 5
                else f"   Params: {query_log.params}"
            )


async def tracking_with_transaction_parameter():
    """Track queries using transaction parameter"""
    print("\n=== Tracking with Transaction Parameter ===")

    user_repo = Repository(User, UserSearch, UserUpdate, "users")
    user_id = uuid4()

    # Method 2: Enable tracking directly in transaction
    async with DatabaseManager.transaction(track_queries=True):
        new_user = User(id=user_id, name="Bob", email="bob@example.com")
        await user_repo.create(new_user)

        await user_repo.find_by_id(user_id)

        # Access the tracker via Repository
        tracker = Repository.get_query_tracker()
        if tracker:
            queries = tracker.get_queries()
            print(f"\nQueries executed: {len(queries)}")
            for query_log in queries:
                print(f"\nSQL: {query_log.query}")
                print(f"Params: {query_log.params}")


async def export_queries_to_dict():
    """Export tracked queries to dictionary format"""
    print("\n=== Export Queries to Dictionary ===")

    user_repo = Repository(User, UserSearch, UserUpdate, "users")

    async with (
        DatabaseManager.transaction(),
        DatabaseManager.track_queries() as tracker,
    ):
        # Perform some operations
        await user_repo.limit(5).get()
        await user_repo.count()

        # Export to dictionary format (useful for logging/debugging)
        queries_dict = tracker.to_dict()

        print("\nQueries as dictionary:")
        import json

        print(json.dumps(queries_dict, indent=2, default=str))


async def conditional_tracking():
    """Demonstrate conditional query tracking"""
    print("\n=== Conditional Tracking ===")

    user_repo = Repository(User, UserSearch, UserUpdate, "users")
    debug_mode = True  # Could be based on environment variable

    async with DatabaseManager.transaction():
        if debug_mode:
            async with DatabaseManager.track_queries() as tracker:
                _users = await user_repo.limit(5).get()
                print(f"\nDebug mode: {tracker.count()} queries executed")
                for query_log in tracker.get_queries():
                    print(f"  - {query_log.query[:60]}...")
        else:
            _users = await user_repo.limit(5).get()
            print("\nNormal mode: no tracking")


async def nested_tracking():
    """Demonstrate nested tracking contexts"""
    print("\n=== Nested Tracking ===")

    user_repo = Repository(User, UserSearch, UserUpdate, "users")

    async with (
        DatabaseManager.transaction(),
        DatabaseManager.track_queries() as outer_tracker,
    ):
        # First operation
        await user_repo.limit(1).get()
        print(f"\nAfter first operation: {outer_tracker.count()} queries")

        # Nested tracking (uses same tracker)
        async with DatabaseManager.track_queries() as inner_tracker:
            await user_repo.count()
            print(f"Inside nested context: {inner_tracker.count()} queries")

            # They're the same tracker
            assert inner_tracker is outer_tracker

        # Another operation
        await user_repo.where("email", "LIKE", "%@example.com").get()
        print(f"After final operation: {outer_tracker.count()} queries")


async def main():
    """Run all examples"""
    # Setup database
    pool = await get_pool()
    await DatabaseManager.add_pool("default", pool)

    try:
        # Run examples
        await basic_query_tracking()
        await tracking_with_fluent_queries()
        await tracking_multiple_operations()
        await tracking_with_transaction_parameter()
        await export_queries_to_dict()
        await conditional_tracking()
        await nested_tracking()

    finally:
        # Cleanup
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())

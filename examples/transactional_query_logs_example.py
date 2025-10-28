"""
Transactional Decorator with Query Logs Example

This example demonstrates how to use the @transactional decorator
with query_logs=True to automatically track queries in decorated functions.
"""

import asyncio
from uuid import uuid4

from examples.db_setup import get_pool
from src.db_context import DatabaseManager, transactional
from src.entities import User, UserSearch, UserUpdate
from src.repository import Repository


# Example 1: Basic usage with query logs enabled
@transactional(query_logs=True)
async def create_user_with_logs(name: str, email: str):
    """Create a user and automatically log all queries"""
    user_repo = Repository(User, UserSearch, UserUpdate, "users")

    user_id = uuid4()
    new_user = User(id=user_id, name=name, email=email)
    created_user = await user_repo.create(new_user)

    # Access the query tracker
    tracker = Repository.get_query_tracker()
    if tracker:
        print(f"\n✓ Created user '{name}'")
        print(f"  Queries executed: {tracker.count()}")
        for i, query_log in enumerate(tracker.get_queries(), 1):
            print(f"  Query {i}: {query_log.query[:60]}...")

    return created_user


# Example 2: Without query logs (default behavior)
@transactional()
async def create_user_without_logs(name: str, email: str):
    """Create a user without query logging"""
    user_repo = Repository(User, UserSearch, UserUpdate, "users")

    user_id = uuid4()
    new_user = User(id=user_id, name=name, email=email)
    created_user = await user_repo.create(new_user)

    tracker = Repository.get_query_tracker()
    print(f"\n✓ Created user '{name}'")
    print(f"  Query tracking: {'Disabled' if tracker is None else 'Enabled'}")

    return created_user


# Example 3: Complex operation with query analysis
@transactional(query_logs=True)
async def create_and_analyze_users(count: int):
    """Create multiple users and analyze the queries"""
    user_repo = Repository(User, UserSearch, UserUpdate, "users")

    # Create multiple users
    users = [
        User(id=uuid4(), name=f"User {i}", email=f"user{i}@example.com")
        for i in range(count)
    ]
    await user_repo.create_many(users)

    # Query users
    found_users = await user_repo.where("name", "LIKE", "User%").get()

    # Count users
    user_count = await user_repo.count()

    # Analyze queries
    tracker = Repository.get_query_tracker()
    if tracker:
        print("\n✓ Operation completed")
        print(f"  Users created: {len(users)}")
        print(f"  Users found: {len(found_users)}")
        print(f"  Total user count: {user_count}")
        print(f"  Total queries executed: {tracker.count()}")

        print("\n  Query breakdown:")
        for i, query_log in enumerate(tracker.get_queries(), 1):
            query_type = query_log.query.split()[0]
            param_count = len(query_log.params)
            print(f"    {i}. {query_type} - {param_count} params")

    return found_users


# Example 4: Export queries for logging
@transactional(query_logs=True)
async def operation_with_audit_log():
    """Perform operations and export queries for audit logging"""
    user_repo = Repository(User, UserSearch, UserUpdate, "users")

    user_id = uuid4()
    new_user = User(id=user_id, name="Audited User", email="audit@example.com")
    await user_repo.create(new_user)

    # Update the user
    await user_repo.update(user_id, UserUpdate(name="Updated Audited User"))

    # Export queries for audit log
    tracker = Repository.get_query_tracker()
    if tracker:
        queries_dict = tracker.to_dict()

        print("\n✓ Operations completed - Audit log:")
        import json

        print(
            json.dumps(
                {
                    "operation": "user_creation_and_update",
                    "queries": queries_dict,
                    "query_count": len(queries_dict),
                },
                indent=2,
                default=str,
            )
        )

    return user_id


# Example 5: Nested decorated functions
@transactional(query_logs=True)
async def outer_operation():
    """Outer operation with query tracking"""
    print("\n=== Outer Operation ===")

    user_repo = Repository(User, UserSearch, UserUpdate, "users")
    user_id = uuid4()

    # Create a user in outer function
    new_user = User(id=user_id, name="Outer User", email="outer@example.com")
    await user_repo.create(new_user)

    # Call inner function (uses same transaction and tracker)
    await inner_operation()

    # Get final query count
    tracker = Repository.get_query_tracker()
    if tracker:
        print("\n✓ All operations completed")
        print(f"  Total queries: {tracker.count()}")

        print("\n  All queries:")
        for i, query_log in enumerate(tracker.get_queries(), 1):
            print(f"    {i}. {query_log.query[:80]}...")


@transactional()  # Uses same transaction from outer
async def inner_operation():
    """Inner operation (shares transaction)"""
    user_repo = Repository(User, UserSearch, UserUpdate, "users")

    # Create another user
    user_id = uuid4()
    new_user = User(id=user_id, name="Inner User", email="inner@example.com")
    await user_repo.create(new_user)

    # This shares the same tracker from outer
    tracker = Repository.get_query_tracker()
    if tracker:
        print(f"  Inner operation query count: {tracker.count()}")


# Example 6: Error handling with query logs
@transactional(query_logs=True)
async def operation_that_may_fail(should_fail: bool = False):
    """Demonstrate query tracking with error handling"""
    user_repo = Repository(User, UserSearch, UserUpdate, "users")

    try:
        user_id = uuid4()
        new_user = User(id=user_id, name="Test User", email="test@example.com")
        await user_repo.create(new_user)

        if should_fail:
            raise ValueError("Simulated error")

        tracker = Repository.get_query_tracker()
        if tracker:
            print(f"\n✓ Success - Queries executed: {tracker.count()}")

        return user_id

    except ValueError as e:
        tracker = Repository.get_query_tracker()
        if tracker:
            print(f"\n✗ Error occurred after {tracker.count()} queries")
            print(f"  Error: {e}")
        raise


# Example 7: Conditional query logging based on environment
async def conditional_logging_example():
    """Show how to conditionally enable query logging"""
    import os

    # Simulate environment variable
    debug_mode = os.getenv("DEBUG_SQL", "false").lower() == "true"

    @transactional(query_logs=debug_mode)
    async def flexible_operation():
        user_repo = Repository(User, UserSearch, UserUpdate, "users")
        user_id = uuid4()
        new_user = User(id=user_id, name="Flex User", email="flex@example.com")
        await user_repo.create(new_user)

        tracker = Repository.get_query_tracker()
        if tracker:
            print(f"\n✓ Debug mode - Queries: {tracker.count()}")
        else:
            print("\n✓ Normal mode - No query tracking")

    await flexible_operation()


async def main():
    """Run all examples"""
    # Setup database
    pool = await get_pool()
    await DatabaseManager.add_pool("default", pool)

    try:
        print("=" * 60)
        print("TRANSACTIONAL DECORATOR WITH QUERY LOGS EXAMPLES")
        print("=" * 60)

        # Example 1: Basic usage
        print("\n1. Basic usage with query logs")
        await create_user_with_logs("Alice", "alice@example.com")

        # Example 2: Without query logs
        print("\n2. Without query logs (default)")
        await create_user_without_logs("Bob", "bob@example.com")

        # Example 3: Complex operation
        print("\n3. Complex operation with analysis")
        await create_and_analyze_users(3)

        # Example 4: Export for audit log
        print("\n4. Export queries for audit logging")
        await operation_with_audit_log()

        # Example 5: Nested operations
        print("\n5. Nested decorated functions")
        await outer_operation()

        # Example 6: Error handling (success case)
        print("\n6. Error handling (success)")
        await operation_that_may_fail(should_fail=False)

        # Example 6b: Error handling (failure case)
        print("\n7. Error handling (with error)")
        try:
            await operation_that_may_fail(should_fail=True)
        except ValueError:
            print("  (Transaction rolled back)")

        # Example 7: Conditional logging
        print("\n8. Conditional query logging")
        await conditional_logging_example()

        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60)

    finally:
        # Cleanup
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())

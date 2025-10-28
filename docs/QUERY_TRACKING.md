# Query Tracking

Query tracking is a powerful debugging and monitoring feature that allows you to capture and inspect all SQL queries executed within a transaction context, along with their parameters and timestamps.

## Overview

The query tracking system provides:
- Automatic query logging with parameters
- Timestamp tracking for performance analysis
- Support for nested tracking contexts
- Enable/disable capability for conditional tracking
- Export to dictionary format for logging/debugging

## Basic Usage

### Method 1: Using `@transactional` Decorator (Recommended)

The simplest way to enable query tracking for a function:

```python
from src.db_context import transactional
from src.repository import Repository

@transactional(query_logs=True)
async def create_user(name: str, email: str):
    user_repo = Repository(User, UserSearch, UserUpdate, "users")

    new_user = User(id=uuid4(), name=name, email=email)
    await user_repo.create(new_user)

    # Access the query tracker
    tracker = Repository.get_query_tracker()
    if tracker:
        print(f"Executed {tracker.count()} queries")
        for query_log in tracker.get_queries():
            print(f"SQL: {query_log.query}")

    return new_user

# Call the decorated function
user = await create_user("Alice", "alice@example.com")
```

### Method 2: Using `track_queries()` Context Manager

The most flexible way to enable query tracking:

```python
from src.db_context import DatabaseManager
from src.repository import Repository

async with DatabaseManager.transaction():
    async with DatabaseManager.track_queries() as tracker:
        # All queries here will be tracked
        post = await post_repo.find_by_id(post_id)
        posts = await post_repo.where("published", True).get()

        # Get all tracked queries
        queries = tracker.get_queries()
        print(f"Executed {tracker.count()} queries")

        for query_log in queries:
            print(f"SQL: {query_log.query}")
            print(f"Params: {query_log.params}")
            print(f"Timestamp: {query_log.timestamp}")
```

### Method 3: Enable via Transaction Parameter

Enable tracking directly when starting a transaction:

```python
async with DatabaseManager.transaction(track_queries=True):
    # All queries here will be tracked
    await post_repo.create(new_post)

    # Access tracker via Repository
    tracker = Repository.get_query_tracker()
    if tracker:
        queries = tracker.get_queries()
```

## QueryTracker API

### Properties and Methods

#### `get_queries() -> list[QueryLog]`
Returns a copy of all logged queries.

```python
queries = tracker.get_queries()
for query_log in queries:
    print(query_log.query, query_log.params)
```

#### `count() -> int`
Returns the number of tracked queries.

```python
print(f"Executed {tracker.count()} queries")
```

#### `clear()`
Clears all tracked queries from the tracker.

```python
tracker.clear()  # Start fresh
```

#### `enable()` / `disable()`
Enable or disable query tracking dynamically.

```python
tracker.disable()  # Stop tracking
await some_operation()  # Not tracked
tracker.enable()  # Resume tracking
```

#### `is_enabled() -> bool`
Check if tracking is currently enabled.

```python
if tracker.is_enabled():
    print("Tracking is active")
```

#### `to_dict() -> list[dict[str, Any]]`
Export tracked queries to dictionary format (useful for logging).

```python
queries_dict = tracker.to_dict()
# [
#   {
#     "query": "SELECT * FROM posts WHERE id = $1",
#     "params": ["123e4567-e89b-12d3-a456-426614174000"],
#     "timestamp": "2025-10-15T00:50:13.635809+00:00"
#   }
# ]
```

## QueryLog Structure

Each tracked query is represented as a `QueryLog` dataclass:

```python
@dataclass
class QueryLog:
    query: str          # The SQL query string
    params: list[Any]   # Query parameters
    timestamp: datetime # UTC timestamp when query was logged
```

## Advanced Usage

### Using the @transactional Decorator

The `@transactional` decorator provides a clean way to enable query tracking:

#### Basic Decorator Usage

```python
@transactional(query_logs=True)
async def perform_operation():
    # All queries automatically tracked
    await repo.create(entity)

    tracker = Repository.get_query_tracker()
    return tracker.get_queries()
```

#### Without Query Logs (Default)

```python
@transactional()  # query_logs=False by default
async def normal_operation():
    await repo.create(entity)
    # No query tracking
```

#### With Function Arguments

```python
@transactional(query_logs=True)
async def create_post(title: str, content: str):
    post = Post(id=uuid4(), title=title, content=content)
    await post_repo.create(post)

    tracker = Repository.get_query_tracker()
    if tracker:
        print(f"Queries: {tracker.count()}")

    return post

# Call with arguments
post = await create_post("My Title", "My Content")
```

#### Nested Decorated Functions

Nested `@transactional` functions share the same transaction and tracker:

```python
@transactional(query_logs=True)
async def outer_function():
    await repo.create(entity1)
    await inner_function()  # Shares same transaction and tracker

    tracker = Repository.get_query_tracker()
    print(f"Total queries: {tracker.count()}")

@transactional()
async def inner_function():
    await repo.create(entity2)
```

### Nested Tracking Contexts

Nested tracking contexts share the same tracker:

```python
async with DatabaseManager.transaction():
    async with DatabaseManager.track_queries() as outer_tracker:
        await post_repo.create(post1)  # Tracked

        async with DatabaseManager.track_queries() as inner_tracker:
            await post_repo.create(post2)  # Also tracked

            # Same tracker instance
            assert inner_tracker is outer_tracker

        # All queries tracked in the same tracker
        print(f"Total queries: {outer_tracker.count()}")
```

### Conditional Tracking

Enable tracking based on environment or debug flags:

```python
import os

debug_mode = os.getenv("DEBUG_SQL") == "true"

async with DatabaseManager.transaction():
    if debug_mode:
        async with DatabaseManager.track_queries() as tracker:
            await perform_operations()
            log_queries(tracker.get_queries())
    else:
        await perform_operations()
```

### Dynamic Enable/Disable

Control tracking granularly:

```python
async with DatabaseManager.transaction():
    async with DatabaseManager.track_queries() as tracker:
        # Track these queries
        await post_repo.where("published", True).get()

        # Don't track these
        tracker.disable()
        await some_heavy_operation()

        # Resume tracking
        tracker.enable()
        await post_repo.count()
```

### Accessing Tracker from Repository

Get the current tracker from anywhere:

```python
async with DatabaseManager.transaction():
    async with DatabaseManager.track_queries():
        await post_repo.create(post)

        # Access from Repository class
        tracker = Repository.get_query_tracker()
        if tracker:
            print(f"Queries so far: {tracker.count()}")
```

## Use Cases

### 1. Debugging Complex Queries

```python
async with DatabaseManager.transaction():
    async with DatabaseManager.track_queries() as tracker:
        # Execute complex operations
        results = await (
            post_repo
            .where("published", True)
            .where("category", "LIKE", "Tech%")
            .order_by_desc("created_at")
            .limit(10)
            .get()
        )

        # See exactly what SQL was generated
        for query_log in tracker.get_queries():
            print(f"SQL: {query_log.query}")
            print(f"Params: {query_log.params}")
```

### 2. Performance Analysis

```python
from datetime import datetime

async with DatabaseManager.transaction():
    async with DatabaseManager.track_queries() as tracker:
        start = datetime.now()
        await perform_operations()
        end = datetime.now()

        duration = (end - start).total_seconds()
        print(f"Executed {tracker.count()} queries in {duration:.2f}s")
        print(f"Average: {duration / tracker.count():.4f}s per query")
```

### 3. Audit Logging

```python
import json

async with DatabaseManager.transaction():
    async with DatabaseManager.track_queries() as tracker:
        await modify_sensitive_data()

        # Log all queries for audit trail
        audit_log = {
            "user_id": current_user.id,
            "operation": "data_modification",
            "queries": tracker.to_dict(),
            "timestamp": datetime.now().isoformat()
        }

        with open("audit.log", "a") as f:
            f.write(json.dumps(audit_log) + "\n")
```

### 4. Testing Query Optimization

```python
async with DatabaseManager.transaction():
    async with DatabaseManager.track_queries() as tracker:
        # Test different query approaches
        await approach_1()
        count_1 = tracker.count()

        tracker.clear()

        await approach_2()
        count_2 = tracker.count()

        print(f"Approach 1: {count_1} queries")
        print(f"Approach 2: {count_2} queries")
```

## Best Practices

1. **Use for Development/Debugging**: Enable query tracking in development and testing environments.

2. **Conditional in Production**: In production, enable only when needed (e.g., for specific debugging scenarios).

3. **Clear When Needed**: Use `tracker.clear()` to reset the tracker if you're analyzing different operations separately.

4. **Performance Impact**: Query tracking has minimal overhead, but in high-throughput scenarios, disable when not needed.

5. **Export for Logging**: Use `tracker.to_dict()` to export queries for structured logging systems.

## Examples

### Context Manager Examples
See `examples/query_tracking_example.py` for complete working examples including:
- Basic query tracking
- Fluent query tracking
- Multiple operations tracking
- Transaction parameter usage
- Query export
- Conditional tracking
- Nested tracking

### Decorator Examples
See `examples/transactional_query_logs_example.py` for `@transactional` decorator examples:
- Basic decorator usage with query logs
- Without query logs (default)
- Complex operations with analysis
- Export queries for audit logging
- Nested decorated functions
- Error handling with query logs
- Conditional query logging

## Testing

Comprehensive tests are available in `tests/query_tracking/` covering:

### Context Manager Tests (`test_query_tracking.py`)
- Basic functionality
- Fluent interface integration
- CRUD operations
- Bulk operations
- Nested contexts
- Enable/disable functionality
- Timestamp tracking
- Multiple repositories

### Decorator Tests (`test_transactional_decorator.py`)
- Decorator with query_logs enabled/disabled
- Return values with query tracking
- Complex operations
- Nested decorated functions
- Exception handling
- Function arguments
- Query export

Run all query tracking tests:
```bash
uv run pytest tests/query_tracking/ -v
```

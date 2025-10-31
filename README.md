# Repysitory

A python package for creating and managing sql repositories.

## GOAL
The goal of this package is to provide a simple way to create and manage sql repositories.
It is designed to be simple and easy to use, while still providing the necessary functionality to manage sql repositories.
It is going to be very opinionated and in some cases a well custom written sql statement will be enough to solve your custom problem.

## Special thanks
To my beautiful wife and kids for their support and patience during the development of this package.
To AI Agents to help me write the code and documentation.


## How to run the tests
1. Requirements
   - Python 3.13 or higher
   - Docker (daemon running) — required for tests that use testcontainers/PostgreSQL
   - Optional: uv (recommended) or pip for dependency management

2. Install dependencies
   Using uv (recommended):
   - Install uv: https://docs.astral.sh/uv/
   - Create and activate venv (uv manages this automatically):
     - uv sync --all-groups
       - This installs both runtime and dev dependencies (pytest, pytest-asyncio, testcontainers, etc.)
   Or using pip:
   - python -m venv .venv && source .venv/bin/activate
   - pip install -e .
   - pip install -r <(printf "pytest\npytest-asyncio\ntestcontainers[postgres]\npytest-cov\n")

3. Run tests
   - Run the whole test suite (requires Docker running for DB-backed tests):
     - uv run pytest -v
     - or: pytest -v
   - Run only the QueryBuilder unit tests (no Docker needed):
     - uv run pytest tests/query_builder -v
     - or: pytest tests/query_builder -v
   - Run a single test file or test case:
     - pytest tests/repository_operations_test.py::TestPostRepositoryOperations::test_create_and_find_by_id -v

4. Notes
   - Database-backed tests spin up a ephemeral PostgreSQL 17 container via testcontainers (see tests/conftest.py). Ensure Docker is running and you have access to pull images.
   - AsyncIO is configured via pytest.ini (asyncio_mode=auto). Tests use async fixtures and transactional context managers provided by src/db_context.py.
   - If you want coverage locally:
     - uv run pytest --cov=src --cov-report=term-missing
   - If Docker pulls are slow or restricted, you can still run QueryBuilder tests which do not require the database:
     - pytest tests/query_builder -q

5. Pro tips
   - Add to your shell: `alias uvr="uv run task"` so you can later do `uvr format` and run commands inside pyproject.toml


## Project tasks (Taskipy + pre-commit)

This project defines a small set of repeatable tasks in pyproject.toml using Taskipy and delegates lint/format to pre-commit.

Prerequisites
- Install dependencies (dev included):
  - uv sync --all-groups
- Install pre-commit hooks locally (once per clone):
  - uv run pre-commit install

Available tasks
- Test (with coverage HTML report to htmlcov/):
  - uv run task test
- Lint (Ruff via pre-commit):
  - uv run task lint
- Format (Ruff formatter via pre-commit):
  - uv run task format
- Run all pre-commit hooks across the repo:
  - uv run task pre-commit-all

Notes
- pre-commit runs additional utilities (trailing-whitespace, end-of-file-fixer) beyond Ruff, so it may produce small whitespace/end-of-file changes even when Ruff shows none.
- Ruff version is pinned to align between pre-commit and the project configuration, ensuring consistent results no matter how you run it.

Tips
- If you added this to your shell earlier: alias uvr="uv run task" you can now run, for example:
  - uvr test
  - uvr lint
  - uvr format
  - uvr pre-commit-all

## Features

### QueryBuilder
- **Fluent SQL Query Building** - Chainable, immutable query builder pattern
- **SELECT Operations**
  - Custom field selection with support for aliases
  - Support for aggregate functions (COUNT, SUM, etc.)
- **WHERE Conditions**
  - Basic conditions with custom operators (=, !=, <, >, <=, >=, LIKE, etc.)
  - `where(field, value)` - defaults to equality
  - `where(field, operator, value)` - custom operator
  - `where_in(field, values)` - IN clause
  - `where_not_in(field, values)` - NOT IN clause
- **OR WHERE Conditions**
  - `or_where(field, value)` - OR conditions
  - `or_where(field, operator, value)` - OR with custom operator
  - `or_where_in(field, values)` - OR with IN clause
  - `or_where_not_in(field, values)` - OR with NOT IN clause
- **Grouped Conditions** - Parenthesized condition groups using lambda functions
  - `where_group(lambda qb: ...)` - AND grouped conditions
  - `or_where_group(lambda qb: ...)` - OR grouped conditions
- **Aggregation & Grouping**
  - `group_by(*fields)` - GROUP BY clause
  - `having(field, operator, value)` - HAVING clause with alias resolution
- **Sorting**
  - `order_by(field)` - ORDER BY (defaults to ASC)
  - `order_by_asc(field)` - Explicit ascending order
  - `order_by_desc(field)` - Descending order
  - Chainable for multi-field sorting
- **Pagination**
  - `limit(count)` - LIMIT clause
  - `offset(count)` - OFFSET clause
  - `paginate(page, per_page)` - Page-based pagination
- **Query Output**
  - `build()` - Returns SQL query and parameters
  - `to_sql()` - Returns only SQL string for debugging

### Repository Pattern
- **Generic Repository** - Type-safe repository with generic Entity, Search, and Update models
- **CRUD Operations**
  - `create(entity)` - Create single entity
  - `create_many(entities)` - Bulk create
  - `find_by_id(id)` - Find by UUID
  - `find_one_by(search)` - Find single entity by search criteria
  - `find_many_by(search, sort)` - Find multiple with sorting
  - `update(id, update_data)` - Update single entity
  - `update_many_by_ids(ids, update_data)` - Bulk update
  - `delete(id)` - Delete by ID
  - `delete_many(ids)` - Bulk delete
- **Fluent Query Interface** - All QueryBuilder methods available on Repository
  - `select(*fields)` - Custom field selection
  - `where(field, value)` - Add WHERE conditions
  - `or_where(field, value)` - Add OR WHERE conditions
  - `where_in(field, values)` - WHERE IN
  - `where_not_in(field, values)` - WHERE NOT IN
  - `order_by(field)` / `order_by_asc(field)` / `order_by_desc(field)` - Sorting
  - `group_by(*fields)` - Grouping
  - `having(field, value)` - HAVING clause
  - `limit(count)` / `offset(count)` - Pagination
  - `paginate(page, per_page)` - Page-based pagination
- **Execution Methods**
  - `get()` - Execute query and return all results
  - `first()` - Execute and return first result
  - `count()` - Return count of matching records
  - `exists()` - Check if any records match
- **Repository Configuration** - Type-safe configuration using `RepositoryConfig`
  - `db_schema` - Optional database schema name for multi-schema support
- **Schema Support** - Multi-schema database support
- **Pydantic Integration** - Full Pydantic model support for entities, search, and updates

### Automatic Field Management ⭐
- **Timestamps** - Simply add `created_at` and/or `updated_at` datetime fields to your schema
- **Soft Delete** - Add `deleted_at: datetime | None` field to enable soft delete
  - `delete()` automatically sets `deleted_at` instead of hard deleting
  - Queries automatically exclude soft-deleted records
  - Use `with_trashed()` to include deleted records
  - Use `only_trashed()` to query only deleted records
  - Use `restore()` to un-delete records
- **No Configuration** - The repository detects these fields automatically
- See `examples/feature_system_example.py` for full examples

### Database Context & Transaction Management
- **Connection Pooling** - Named database pool management with `DatabaseManager`
- **Transaction Context Manager** - `async with DatabaseManager.transaction():`
- **Nested Transaction Support** - Automatic detection and handling of nested transactions
- **Transactional Decorator** - `@transactional(db_name)` decorator for automatic transaction wrapping
- **Context-Aware Connections** - ContextVar-based connection management for async safety
- **Multi-Database Support** - Named database pools for multiple database connections

### Entity & Mapping
- **Pydantic-Based Entities** - Type-safe entity definitions using Pydantic
- **Base Entity Class** - UUID primary key support with auto-generation
- **Automatic Row Mapping** - Database row to entity object mapping
- **Enum Support** - Built-in enum value handling (e.g., SortOrder)
- **Dynamic Entity Classes** - Runtime entity class creation with timestamp fields

### Search & Sorting
- **Type-Safe Search Models** - Pydantic-based search criteria
- **Type-Safe Update Models** - Pydantic-based partial update models
- **Dynamic Sorting** - Sort models with ASC/DESC enum support
- **Null-Safe Filtering** - Automatic filtering of None values in search criteria

## Usage Examples

### Repository Configuration

Configure your repository with optional settings using `RepositoryConfig`:

```python
from src.repository import Repository, RepositoryConfig

# Basic repository without configuration
repo = Repository(
    entity_class=Post,
    search_class=PostSearch,
    update_class=PostUpdate,
    table_name="posts"
)

# Repository with database schema
repo = Repository(
    entity_class=Post,
    search_class=PostSearch,
    update_class=PostUpdate,
    table_name="posts",
    config=RepositoryConfig(db_schema="app")
)

# Repository with automatic timestamps
repo = Repository(
    entity_class=Post,
    search_class=PostSearch,
    update_class=PostUpdate,
    table_name="posts",
    config=RepositoryConfig(timestamps=True)
)

# Repository with both schema and timestamps
repo = Repository(
    entity_class=Post,
    search_class=PostSearch,
    update_class=PostUpdate,
    table_name="posts",
    config=RepositoryConfig(db_schema="app", timestamps=True)
)
```

The `RepositoryConfig` model provides a type-safe way to configure repositories and makes it easy to add new configuration options in the future.

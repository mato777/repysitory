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

import asyncio

import pytest

from src.db_context import DatabaseManager


@pytest.mark.asyncio
async def test_connection_released_on_exception_sequential():
    """Ensure that connections acquired via pool.acquire() are released even when an
    exception happens inside the transaction context. We iterate more times than the
    pool size; if releases didn't happen, this would block/exhaust the pool.
    """
    # Run more iterations than pool max_size (configured as 5 in tests/conftest.py)
    iterations = 20

    for _ in range(iterations):
        try:
            async with DatabaseManager.transaction("test_db"):
                # Do a trivial statement to touch the DB
                pass
                # Raise an error to force rollback and context exit via exception
                raise RuntimeError("forced error to test release")
        except RuntimeError:
            # Expected; loop should keep progressing without blockage
            pass


@pytest.mark.asyncio
async def test_connection_released_on_exception_concurrent():
    """Ensure that multiple concurrent failing transactions don't deadlock or exhaust the pool
    because each acquired connection is properly released on exception."""

    async def failing_tx():
        try:
            async with DatabaseManager.transaction("test_db"):
                # Simulate some small async work
                await asyncio.sleep(0)
                raise RuntimeError("boom")
        except RuntimeError:
            return True

    # Launch more tasks than pool size to verify fair scheduling and release
    tasks = [asyncio.create_task(failing_tx()) for _ in range(10)]

    done, pending = await asyncio.wait(tasks, timeout=5)

    assert not pending, (
        "Some transactions did not finish; connections may not have been released"
    )
    assert all(t.result() is True for t in done)

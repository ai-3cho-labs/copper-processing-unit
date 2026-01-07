"""
$COPPER Async Utilities

Shared async utilities for Celery tasks and other sync contexts.
"""

import asyncio
from typing import TypeVar, Coroutine, Any

T = TypeVar('T')


def run_async(coro: Coroutine[Any, Any, T]) -> T:
    """
    Run an async coroutine from a sync context.

    Used by Celery tasks to execute async service methods.

    Args:
        coro: Async coroutine to execute.

    Returns:
        Result of the coroutine.
    """
    # Use asyncio.run() for Python 3.7+ - cleaner than manual loop management
    return asyncio.run(coro)


async def gather_with_concurrency(n: int, *coros: Coroutine) -> list:
    """
    Run coroutines with limited concurrency.

    Args:
        n: Maximum number of concurrent coroutines.
        coros: Coroutines to execute.

    Returns:
        List of results in same order as input.
    """
    semaphore = asyncio.Semaphore(n)

    async def sem_coro(coro):
        async with semaphore:
            return await coro

    return await asyncio.gather(*(sem_coro(c) for c in coros))

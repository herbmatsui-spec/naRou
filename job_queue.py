"""Job Queue with priority support.
Provides a lightweight wrapper around `heapq` allowing jobs (callables) to be
scheduled with an integer priority (lower number = higher priority)."""

from __future__ import annotations

import heapq
import itertools
from collections.abc import Callable
from typing import Any


class JobQueue:
    """Priority queue for background jobs.
    Each job is a callable with optional args/kwargs stored internally.
    """

    def __init__(self):
        self._heap: list[tuple[int, int, Callable, tuple, dict]] = []
        self._counter = itertools.count()  # tie‑breaker for same priority

    def add_job(
        self,
        func: Callable,
        *,
        priority: int = 10,
        args: tuple = (),
        kwargs: dict = None,
    ) -> None:
        """Add a job to the queue.
        Args:
            func: Callable to execute.
            priority: Numeric priority (lower = earlier). Default 10.
            args: Positional arguments for the callable.
            kwargs: Keyword arguments for the callable.
        """
        if kwargs is None:
            kwargs = {}
        count = next(self._counter)
        heapq.heappush(self._heap, (priority, count, func, args, kwargs))

    def run_next(self) -> Any:
        """Execute the highest‑priority job and return its result.
        Raises IndexError if the queue is empty.
        """
        if not self._heap:
            raise IndexError("JobQueue is empty")
        priority, count, func, args, kwargs = heapq.heappop(self._heap)
        return func(*args, **kwargs)

    def __len__(self) -> int:
        return len(self._heap)


# Example usage (not executed in production):
# def hello(name):
#     return f"Hello {name}"
# q = JobQueue()
# q.add_job(hello, priority=5, args=("World",))
# print(q.run_next())

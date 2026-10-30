"""
Tiny in-memory failure limiter used for login and password-recovery requests.

It is per-process: with several workers each keeps its own counters, so treat it as a brake
against casual guessing, not a replacement for an edge/WAF rate limit.
"""

import time
from collections import defaultdict, deque

from fastapi import HTTPException


class FailureLimiter:
    def __init__(self, max_failures: int, window_seconds: int):
        self.max_failures = max_failures
        self.window = window_seconds
        self._events: dict[str, deque[float]] = defaultdict(deque)

    def _prune(self, key: str) -> deque:
        events = self._events[key]
        cutoff = time.monotonic() - self.window
        while events and events[0] < cutoff:
            events.popleft()
        if not events:
            self._events.pop(key, None)
            return deque()
        return events

    def check(self, key: str) -> None:
        if len(self._prune(key)) >= self.max_failures:
            raise HTTPException(status_code=429, detail="Too many attempts. Please wait a few minutes and try again.")

    def record(self, key: str) -> None:
        self._prune(key)
        self._events[key].append(time.monotonic())

    def reset(self, key: str) -> None:
        self._events.pop(key, None)

    def clear(self) -> None:
        self._events.clear()

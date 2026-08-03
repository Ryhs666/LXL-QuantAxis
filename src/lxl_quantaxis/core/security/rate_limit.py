"""Small in-process rate limiter used by local authentication endpoints."""

from __future__ import annotations

import math
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RateLimitDecision:
    """Result returned by a rate-limit check."""

    allowed: bool
    retry_after_seconds: int = 0


class InMemoryRateLimiter:
    """Thread-safe sliding-window limiter for a single application process."""

    def __init__(
        self,
        clock: Callable[[], float] = time.monotonic,
        max_keys: int = 10_000,
    ) -> None:
        if max_keys < 1:
            raise ValueError("max_keys must be positive")
        self._clock = clock
        self._max_keys = max_keys
        self._attempts: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def check(
        self,
        key: str,
        *,
        limit: int,
        window_seconds: int,
    ) -> RateLimitDecision:
        if not key:
            raise ValueError("key cannot be empty")
        if limit < 1 or window_seconds < 1:
            raise ValueError("limit and window_seconds must be positive")

        now = self._clock()
        cutoff = now - window_seconds
        with self._lock:
            attempts = self._attempts.get(key)
            if attempts is None:
                if len(self._attempts) >= self._max_keys:
                    self._remove_oldest_bucket()
                attempts = deque()
                self._attempts[key] = attempts

            while attempts and attempts[0] <= cutoff:
                attempts.popleft()

            if len(attempts) >= limit:
                retry_after = max(1, math.ceil(window_seconds - (now - attempts[0])))
                return RateLimitDecision(False, retry_after)

            attempts.append(now)
            return RateLimitDecision(True)

    def reset(self, key: str) -> None:
        with self._lock:
            self._attempts.pop(key, None)

    def _remove_oldest_bucket(self) -> None:
        oldest_key = min(
            self._attempts,
            key=lambda item: self._attempts[item][-1],
        )
        self._attempts.pop(oldest_key, None)

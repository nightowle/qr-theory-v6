from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class TokenBucket:
    capacity: int
    refill_rate: float

    def __post_init__(self) -> None:
        self._tokens = float(self.capacity)
        self._last_check = time.monotonic()

    def consume(self, tokens: float = 1.0) -> bool:
        now = time.monotonic()
        elapsed = now - self._last_check
        self._last_check = now
        self._tokens = min(self.capacity, self._tokens + elapsed * self.refill_rate)
        if self._tokens >= tokens:
            self._tokens -= tokens
            return True
        return False


__all__ = ["TokenBucket"]

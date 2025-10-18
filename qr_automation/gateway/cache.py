from __future__ import annotations

import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class CacheEntry:
    value: Any
    expires_at: float


class TTLCache:
    """Einfacher TTL-Cache mit LRU-Verdrängung."""

    def __init__(self, max_entries: int, ttl_seconds: float) -> None:
        self._entries: "OrderedDict[str, CacheEntry]" = OrderedDict()
        self._max_entries = max_entries
        self._ttl = ttl_seconds

    def _purge(self) -> None:
        now = time.monotonic()
        keys_to_remove = [key for key, entry in self._entries.items() if entry.expires_at <= now]
        for key in keys_to_remove:
            self._entries.pop(key, None)

    def get(self, key: str) -> Optional[Any]:
        self._purge()
        entry = self._entries.get(key)
        if not entry:
            return None
        self._entries.move_to_end(key)
        return entry.value

    def set(self, key: str, value: Any) -> None:
        self._purge()
        expires_at = time.monotonic() + self._ttl
        self._entries[key] = CacheEntry(value=value, expires_at=expires_at)
        self._entries.move_to_end(key)
        while len(self._entries) > self._max_entries:
            self._entries.popitem(last=False)

    def clear(self) -> None:
        self._entries.clear()


__all__ = ["TTLCache", "CacheEntry"]

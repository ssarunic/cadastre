"""The cache that stores nothing, and the one that puts a memory front before another backend."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from . import policy
from .stats import CacheStats

if TYPE_CHECKING:
    from .protocol import ResponseCache


class NullCache:
    """Cache off: every lookup is a miss and nothing is kept."""

    backend = "off"

    def __init__(self) -> None:
        self._misses = 0

    def get(self, key: str) -> bytes | None:
        self._misses += 1
        return None

    def set(self, key: str, value: bytes, ttl: float) -> None:
        return None

    def delete(self, key: str) -> None:
        return None

    def clear(self) -> None:
        return None

    def stats(self) -> CacheStats:
        return CacheStats(self.backend, entries=0, bytes=0, hits=0, misses=self._misses)


class TieredCache:
    """A memory front before a slower back (disk or a cache service).

    ``get`` reads the front, then the back; a back hit fills the front for
    the lifetime the entry has left, read from its envelope, so the two
    never disagree about expiry. ``set``, ``delete`` and ``clear`` go to
    both. The stats count this cache's own hits and misses and report the
    back's holdings, the fuller of the two.
    """

    def __init__(self, front: ResponseCache, back: ResponseCache) -> None:
        self.front = front
        self.back = back
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> bytes | None:
        value = self.front.get(key)
        if value is None:
            value = self.back.get(key)
            if value is not None:
                envelope = policy.decode(value)
                remaining = (
                    envelope.remaining_lifetime(datetime.now(timezone.utc)) if envelope else 0.0
                )
                if remaining > 0:
                    self.front.set(key, value, remaining)
        if value is None:
            self._misses += 1
        else:
            self._hits += 1
        return value

    def set(self, key: str, value: bytes, ttl: float) -> None:
        self.front.set(key, value, ttl)
        self.back.set(key, value, ttl)

    def delete(self, key: str) -> None:
        self.front.delete(key)
        self.back.delete(key)

    def clear(self) -> None:
        self.front.clear()
        self.back.clear()

    def stats(self) -> CacheStats:
        front, back = self.front.stats(), self.back.stats()
        return CacheStats(
            backend=f"{front.backend}+{back.backend}",
            entries=back.entries,
            bytes=back.bytes,
            hits=self._hits,
            misses=self._misses,
        )


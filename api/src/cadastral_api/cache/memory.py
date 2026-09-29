"""Layer 1: an in-process memory cache with one byte budget and per-entry lifetimes."""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable

from cachetools import TLRUCache

from .stats import CacheStats

logger = logging.getLogger(__name__)

DEFAULT_MEMORY_MB = 64.0


class MemoryCache:
    """Bytes held in the process, least recently used out first, each with its own lifetime.

    One ``cachetools.TLRUCache`` measured in bytes (``getsizeof`` is the
    length of the value) holds every entry; the lifetime passed to ``set``
    becomes that entry's expiry, so classes with different lifetimes share
    the one budget. A ``threading.Lock`` guards it, since the MCP server
    reads and writes from worker threads. ``timer`` is monotonic seconds
    and can be replaced in tests to move time forward.
    """

    backend = "memory"

    def __init__(
        self,
        max_bytes: int = int(DEFAULT_MEMORY_MB * 1024 * 1024),
        *,
        timer: Callable[[], float] = time.monotonic,
    ) -> None:
        if max_bytes <= 0:
            raise ValueError(f"max_bytes must be positive, got {max_bytes}")
        self.max_bytes = max_bytes
        self._lock = threading.Lock()
        self._entries: TLRUCache[str, tuple[bytes, float]] = TLRUCache(
            maxsize=max_bytes,
            ttu=lambda _key, value, now: now + value[1],
            timer=timer,
            getsizeof=lambda value: len(value[0]),
        )
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> bytes | None:
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                self._misses += 1
                return None
            self._hits += 1
            return entry[0]

    def set(self, key: str, value: bytes, ttl: float) -> None:
        if ttl <= 0:
            self.delete(key)
            return
        with self._lock:
            try:
                self._entries[key] = (bytes(value), float(ttl))
            except ValueError:
                # Larger than the whole budget: not cacheable, not an error.
                logger.debug(
                    "Response of %d bytes exceeds the cache budget; not stored", len(value)
                )
                self._entries.pop(key, None)

    def delete(self, key: str) -> None:
        with self._lock:
            self._entries.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def stats(self) -> CacheStats:
        with self._lock:
            self._entries.expire()
            return CacheStats(
                backend=self.backend,
                entries=len(self._entries),
                bytes=int(self._entries.currsize),
                hits=self._hits,
                misses=self._misses,
            )

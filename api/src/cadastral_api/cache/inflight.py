"""Per-key locks so that concurrent identical requests make one upstream fetch (section 4.3)."""

from __future__ import annotations

import threading
from collections.abc import Iterator
from contextlib import contextmanager


class Inflight:
    """``with inflight(key):`` serialises the callers of one key.

    A lock is created when the first caller of a key arrives and dropped
    when the last one leaves, so a long-lived process never accumulates
    one lock per request it has ever made.
    """

    def __init__(self) -> None:
        self._registry = threading.Lock()
        self._locks: dict[str, tuple[threading.Lock, int]] = {}

    @contextmanager
    def __call__(self, key: str) -> Iterator[None]:
        with self._registry:
            lock, waiters = self._locks.get(key, (threading.Lock(), 0))
            self._locks[key] = (lock, waiters + 1)
        lock.acquire()
        try:
            yield
        finally:
            lock.release()
            with self._registry:
                lock, waiters = self._locks[key]
                if waiters <= 1:
                    del self._locks[key]
                else:
                    self._locks[key] = (lock, waiters - 1)

    def __len__(self) -> int:
        """How many keys have a request in flight or waiting."""
        with self._registry:
            return len(self._locks)

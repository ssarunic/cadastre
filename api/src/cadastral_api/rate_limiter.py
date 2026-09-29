"""One request per interval, whoever asks and from whichever thread.

The MCP server runs tool calls in worker threads, so several callers can
reach the upstream at once. The limiter hands each caller the next free
slot in arrival order and lets it sleep until then: N concurrent callers
become N requests exactly one interval apart, never a burst.
"""

from __future__ import annotations

import threading
import time


class RateLimiter:
    """A minimum interval between the requests of everyone sharing the limiter.

    ``wait()`` reserves the next slot under a lock (held for microseconds)
    and sleeps outside it, so a long queue never blocks the bookkeeping. A
    clock adjustment cannot open a burst: slots are measured on the
    monotonic clock.

    Args:
        interval: Seconds between two requests; 0 disables the wait.
    """

    def __init__(self, interval: float) -> None:
        if interval < 0:
            raise ValueError(f"interval must not be negative, got {interval}")
        self.interval = interval
        self._lock = threading.Lock()
        self._next_slot = 0.0

    def reserve(self) -> float:
        """Take the next free slot; the seconds to wait before using it (0 when free)."""
        with self._lock:
            now = time.monotonic()
            slot = max(now, self._next_slot)
            self._next_slot = slot + self.interval
        return slot - now

    def wait(self) -> float:
        """Block until this caller's slot; the seconds it waited."""
        delay = self.reserve()
        if delay > 0:
            time.sleep(delay)
        return delay

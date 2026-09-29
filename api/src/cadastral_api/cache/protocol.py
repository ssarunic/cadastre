"""The one interface every backend implements (section 4)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .stats import CacheStats


@runtime_checkable
class ResponseCache(Protocol):
    """Bytes in, bytes out, with a lifetime per entry."""

    def get(self, key: str) -> bytes | None:
        """The stored bytes, or None when absent, expired or unreadable."""
        ...

    def set(self, key: str, value: bytes, ttl: float) -> None:
        """Store ``value`` for ``ttl`` seconds; a non-positive lifetime removes the key."""
        ...

    def delete(self, key: str) -> None:
        """Remove one entry; absent is not an error."""
        ...

    def clear(self) -> None:
        """Remove every entry this backend holds."""
        ...

    def stats(self) -> CacheStats:
        """Backend name, holdings and the hit and miss counts of this process."""
        ...

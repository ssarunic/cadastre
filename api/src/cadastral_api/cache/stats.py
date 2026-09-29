"""What a backend reports about itself."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CacheStats:
    """Backend name, what it holds and how the lookups of this process went."""

    backend: str
    entries: int
    bytes: int
    hits: int
    misses: int

    @property
    def hit_ratio(self) -> float | None:
        """Hits over lookups, or None before the first lookup."""
        lookups = self.hits + self.misses
        return self.hits / lookups if lookups else None

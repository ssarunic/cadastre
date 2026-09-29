"""Cache of upstream responses behind one interface (``specs/response-cache-specification.md``).

The client stores the JSON the upstream sent, as bytes, under a key derived
from the request, for a lifetime fixed by the endpoint's data class
(:mod:`.policy`). Which backend holds the bytes is configuration:
``memory`` (the default, in-process) or ``off``; the disk and service
layers come with later phases behind the same :class:`ResponseCache`.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

from .inflight import Inflight
from .memory import DEFAULT_MEMORY_MB, MemoryCache
from .protocol import ResponseCache
from .stats import CacheStats
from .tiered import NullCache, TieredCache

logger = logging.getLogger(__name__)

#: Backends the configuration may name; the ones not in this version fall
#: back to memory with a warning (section 4.5).
KNOWN_BACKENDS = ("memory", "off", "disk", "redis")
_UNAVAILABLE = ("disk", "redis")


@dataclass(frozen=True)
class Fetched:
    """What one request returned: the body, when the upstream sent it, and how it was got.

    ``from_cache`` is what a gateway reports as ``X-Cache: HIT|MISS``.
    """

    body: Any
    fetched_at: str
    from_cache: bool


def from_config(
    value: ResponseCache | str | None = None,
    *,
    memory_mb: float | None = None,
) -> ResponseCache:
    """The backend the configuration names.

    ``value`` is a ready backend (returned as is), ``"memory"`` or ``"off"``,
    or None for ``CADASTRAL_CACHE`` (default ``memory``). ``memory_mb`` is
    the byte budget of the memory layer, else ``CADASTRAL_CACHE_MEMORY_MB``
    (default 64). ``disk`` and ``redis://...`` are named by the
    specification but not available in this version: they log a warning
    and give the memory layer. Any other value is a ``ValueError``.
    """
    if value is not None and not isinstance(value, str):
        return value
    spec = (value if value is not None else os.getenv("CADASTRAL_CACHE", "memory")).strip()
    kind = spec.split("://", 1)[0].lower() if spec else "memory"
    if kind == "off":
        return NullCache()
    if kind in _UNAVAILABLE:
        logger.warning(
            "CADASTRAL_CACHE=%s is not available in this version; using the memory cache", spec
        )
        kind = "memory"
    if kind != "memory":
        raise ValueError(
            f"CADASTRAL_CACHE must be one of {', '.join(KNOWN_BACKENDS)} "
            f"(redis as a redis:// URL), got {spec!r}"
        )
    if memory_mb is None:
        raw = os.getenv("CADASTRAL_CACHE_MEMORY_MB", str(DEFAULT_MEMORY_MB))
        try:
            memory_mb = float(raw)
        except ValueError as e:
            raise ValueError(f"CADASTRAL_CACHE_MEMORY_MB must be a number, got {raw!r}") from e
    return MemoryCache(max_bytes=max(1, int(memory_mb * 1024 * 1024)))


__all__ = [
    "CacheStats",
    "Fetched",
    "Inflight",
    "MemoryCache",
    "NullCache",
    "ResponseCache",
    "TieredCache",
    "from_config",
]

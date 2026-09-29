"""Contract of every response-cache backend (specs/response-cache-specification.md, section 10).

One suite, run against each backend: set then get, expiry on a fake clock,
delete, clear, the byte budget, and that a value comes back equal. Bytes
are immutable, so no caller can change a stored value through the object
it gets; equality is the whole contract.
"""

from __future__ import annotations

import pytest

from cadastral_api.cache import (
    CacheStats,
    MemoryCache,
    NullCache,
    ResponseCache,
    TieredCache,
    policy,
)


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def _memory(clock: FakeClock, max_bytes: int = 1024) -> MemoryCache:
    return MemoryCache(max_bytes=max_bytes, timer=clock)


def _tiered(clock: FakeClock, max_bytes: int = 1024) -> TieredCache:
    return TieredCache(_memory(clock, max_bytes), _memory(clock, max_bytes))


@pytest.fixture(params=["memory", "tiered"])
def backend(request) -> tuple[ResponseCache, FakeClock]:
    clock = FakeClock()
    return (_memory(clock) if request.param == "memory" else _tiered(clock)), clock


def test_set_then_get_returns_equal_bytes(backend) -> None:
    cache, _ = backend
    cache.set("k", b"value", ttl=60)
    assert cache.get("k") == b"value"
    assert cache.get("absent") is None


def test_entries_expire_on_the_clock(backend) -> None:
    cache, clock = backend
    cache.set("k", b"value", ttl=60)
    clock.now += 59
    assert cache.get("k") == b"value"
    clock.now += 2
    assert cache.get("k") is None


def test_delete_and_clear(backend) -> None:
    cache, _ = backend
    cache.set("a", b"1", ttl=60)
    cache.set("b", b"2", ttl=60)
    cache.delete("a")
    cache.delete("never-there")
    assert cache.get("a") is None and cache.get("b") == b"2"
    cache.clear()
    assert cache.get("b") is None
    assert cache.stats().entries == 0


def test_non_positive_lifetime_removes_the_entry(backend) -> None:
    cache, _ = backend
    cache.set("k", b"value", ttl=60)
    cache.set("k", b"value", ttl=0)
    assert cache.get("k") is None


def test_stats_count_hits_misses_entries_and_bytes(backend) -> None:
    cache, _ = backend
    cache.get("k")
    cache.set("k", b"12345", ttl=60)
    cache.get("k")
    stats = cache.stats()
    assert isinstance(stats, CacheStats)
    assert (stats.entries, stats.bytes, stats.hits, stats.misses) == (1, 5, 1, 1)
    assert stats.hit_ratio == 0.5


def test_byte_budget_evicts_least_recently_used() -> None:
    clock = FakeClock()
    cache = _memory(clock, max_bytes=10)
    cache.set("a", b"1234", ttl=60)
    cache.set("b", b"1234", ttl=60)
    assert cache.get("a") == b"1234"  # "a" is now the more recently used
    cache.set("c", b"1234", ttl=60)  # 12 bytes > 10: "b" goes
    assert cache.get("b") is None
    assert cache.get("a") == b"1234" and cache.get("c") == b"1234"
    assert cache.stats().bytes <= 10


def test_a_value_larger_than_the_budget_is_not_stored_and_not_an_error() -> None:
    cache = _memory(FakeClock(), max_bytes=10)
    cache.set("big", b"x" * 11, ttl=60)
    assert cache.get("big") is None
    assert cache.stats().entries == 0


def test_memory_cache_rejects_a_non_positive_budget() -> None:
    with pytest.raises(ValueError):
        MemoryCache(max_bytes=0)


def test_null_cache_keeps_nothing() -> None:
    cache = NullCache()
    cache.set("k", b"value", ttl=60)
    assert cache.get("k") is None
    cache.delete("k")
    cache.clear()
    assert cache.stats() == CacheStats("off", entries=0, bytes=0, hits=0, misses=1)
    assert cache.stats().hit_ratio == 0.0


def test_backends_satisfy_the_protocol() -> None:
    clock = FakeClock()
    for cache in (NullCache(), _memory(clock), _tiered(clock)):
        assert isinstance(cache, ResponseCache)


class TestTiered:
    def _envelope(self, fetched_at: str) -> bytes:
        return policy.encode(
            {"x": 1}, fetched_at=fetched_at, endpoint="/lr/lr-unit", data_class="lr_unit"
        )

    def test_a_back_hit_fills_the_front_for_the_remaining_lifetime(self) -> None:
        from datetime import datetime, timedelta, timezone

        clock = FakeClock()
        cache = _tiered(clock)
        ten_minutes_ago = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
        raw = self._envelope(ten_minutes_ago)
        cache.back.set("k", raw, ttl=1200)
        assert cache.front.get("k") is None
        assert cache.get("k") == raw
        assert cache.front.get("k") == raw
        # The lr_unit class lives 30 min; 10 have passed, so the front copy
        # dies about 20 min from now, not 30.
        clock.now += 21 * 60
        assert cache.front.get("k") is None

    def test_an_expired_or_unreadable_back_entry_is_served_but_not_promoted(self) -> None:
        clock = FakeClock()
        cache = _tiered(clock)
        cache.back.set("k", b"not an envelope", ttl=60)
        assert cache.get("k") == b"not an envelope"
        assert cache.front.get("k") is None

    def test_set_delete_clear_reach_both_tiers(self) -> None:
        cache = _tiered(FakeClock())
        cache.set("k", b"v", ttl=60)
        assert cache.front.get("k") == b"v" and cache.back.get("k") == b"v"
        cache.delete("k")
        assert cache.front.get("k") is None and cache.back.get("k") is None
        cache.set("k", b"v", ttl=60)
        cache.clear()
        assert cache.back.stats().entries == 0

    def test_stats_name_both_tiers(self) -> None:
        cache = _tiered(FakeClock())
        cache.set("k", b"v", ttl=60)
        cache.get("k")
        cache.get("missing")
        stats = cache.stats()
        assert stats.backend == "memory+memory"
        assert (stats.entries, stats.hits, stats.misses) == (1, 1, 1)

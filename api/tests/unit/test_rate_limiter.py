"""The rate limiter spaces concurrent callers one interval apart, never a burst."""

import threading
import time

import pytest

from cadastral_api.rate_limiter import RateLimiter


def test_zero_interval_never_waits() -> None:
    limiter = RateLimiter(0)
    assert limiter.wait() == 0
    assert limiter.wait() == 0


def test_negative_interval_is_rejected() -> None:
    with pytest.raises(ValueError):
        RateLimiter(-1)


def test_reservations_queue_in_arrival_order() -> None:
    limiter = RateLimiter(1.0)
    first, second, third = limiter.reserve(), limiter.reserve(), limiter.reserve()
    assert first == 0
    assert 0.9 < second <= 1.0
    assert 1.9 < third <= 2.0


def test_threads_are_spaced_by_the_interval() -> None:
    interval = 0.1
    limiter = RateLimiter(interval)
    done: list[float] = []
    lock = threading.Lock()

    def request() -> None:
        limiter.wait()
        with lock:
            done.append(time.monotonic())

    threads = [threading.Thread(target=request) for _ in range(5)]
    start = time.monotonic()
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    done.sort()
    gaps = [b - a for a, b in zip(done, done[1:])]
    # A thread may record its time a little late; the gap may shrink by that
    # much but a burst would show as a gap near zero.
    assert all(gap >= interval * 0.7 for gap in gaps), gaps
    assert done[-1] - start >= 4 * interval * 0.9

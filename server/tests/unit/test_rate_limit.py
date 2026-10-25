from __future__ import annotations

from datetime import timedelta

from app.core.rate_limit import FailureLimiter
from tests.conftest import FixedClock


def test_blocks_after_max_failures_then_expires(fixed_clock: FixedClock) -> None:
    limiter = FailureLimiter(timedelta(minutes=15), fixed_clock)
    for _ in range(5):
        assert not limiter.is_blocked("k", 5)
        limiter.record_failure("k")
    assert limiter.is_blocked("k", 5)
    assert not limiter.is_blocked("khac", 5)
    fixed_clock.at += timedelta(minutes=15, seconds=1)
    assert not limiter.is_blocked("k", 5)


def test_reset_clears_failures(fixed_clock: FixedClock) -> None:
    limiter = FailureLimiter(timedelta(minutes=15), fixed_clock)
    for _ in range(5):
        limiter.record_failure("k")
    limiter.reset("k")
    assert not limiter.is_blocked("k", 5)

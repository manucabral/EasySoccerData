"""FBref admission respects shared windows under concurrency and clock changes."""

import threading
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock

import pytest

from esd.fbref.exceptions import RateLimitExceeded
from esd.fbref.utils import rate_limit


def test_concurrent_admissions_do_not_exceed_one_shared_slot(monkeypatch):
    local, gate = threading.local(), threading.Barrier(2)

    def clock():
        local.calls = getattr(local, "calls", 0) + 1
        # The old implementation checked the deque then read the clock again
        # before appending; both workers could pass admission before either append.
        if local.calls == 2:
            gate.wait(timeout=3)
        return 100.0

    monkeypatch.setattr("esd.fbref.utils.time.time", clock)
    monkeypatch.setattr("esd.fbref.utils.time.monotonic", clock)

    @rate_limit(calls=1, period=60)
    def limited():
        return "allowed"

    start = threading.Barrier(2)

    def call():
        start.wait(timeout=3)
        try:
            return limited()
        except RateLimitExceeded:
            return "blocked"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: call(), range(2)))
    assert sorted(results) == ["allowed", "blocked"]


def test_expiry_uses_monotonic_time_and_failed_attempts_consume_slots(monkeypatch):
    clock = Mock(return_value=100.0)
    monkeypatch.setattr("esd.fbref.utils.time.monotonic", clock)
    monkeypatch.setattr("esd.fbref.utils.time.time", lambda: -100000.0)
    target = Mock(side_effect=RuntimeError("fetch failed"))
    limited = rate_limit(calls=1, period=10)(target)
    with pytest.raises(RuntimeError, match="fetch failed"):
        limited()
    clock.return_value = 109.999
    with pytest.raises(RateLimitExceeded, match="Retry in"):
        limited()
    target.assert_called_once()
    clock.return_value = 110.0
    target.side_effect = None
    target.return_value = "recovered"
    assert limited() == "recovered"


@pytest.mark.parametrize("options", [{"calls": 0}, {"calls": -1}, {"calls": True}, {"calls": 1.5},
    {"period": 0}, {"period": -1}, {"period": float("inf")}, {"period": float("nan")}, {"period": True}])
def test_invalid_limits_fail_when_configured(options):
    with pytest.raises(ValueError):
        rate_limit(**options)

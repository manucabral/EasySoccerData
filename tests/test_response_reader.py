"""Memory and disk response reuse apply the same freshness boundaries."""

from unittest.mock import Mock

import pytest

from esd._response_reader import ResponseReader
from esd.cache import ResponseCache


@pytest.mark.parametrize("persistent", [False, True])
@pytest.mark.parametrize("ttl", [30, lambda _: 30])
def test_backward_wall_clock_does_not_reuse_future_response(tmp_path, monkeypatch, persistent, ttl):
    clock = Mock(return_value=100.0)
    monkeypatch.setattr("esd._response_reader.time.time", clock)
    fetch = Mock(side_effect=[{"value": "old"}, {"value": "new"}])
    reader = ResponseReader(fetch, cache=ResponseCache(tmp_path) if persistent else None)
    assert reader.read("example", ttl=ttl) == {"value": "old"}
    clock.return_value = 99.0
    assert reader.read("example", ttl=ttl) == {"value": "new"}
    assert fetch.call_count == 2 and not reader.last_response.cached
    assert reader.last_response.fetched_at == 99.0


@pytest.mark.parametrize("persistent", [False, True])
@pytest.mark.parametrize("ttl", [0, -1, float("nan"), float("inf")])
def test_nonpositive_or_nonfinite_ttl_never_reuses_response(tmp_path, monkeypatch, persistent, ttl):
    monkeypatch.setattr("esd._response_reader.time.time", lambda: 100.0)
    fetch = Mock(return_value={"ok": True})
    reader = ResponseReader(fetch, cache=ResponseCache(tmp_path) if persistent else None)
    reader.read("example", ttl=30)
    reader.read("example", ttl=ttl)
    assert fetch.call_count == 2 and not reader.last_response.cached

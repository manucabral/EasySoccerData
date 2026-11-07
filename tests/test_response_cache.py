"""Persistent response freshness, corruption recovery and atomic writes."""

import json
from datetime import datetime, timedelta, timezone

import pytest

import esd.cache as cache_module
from esd import CacheError, CachePolicy, ResponseCache


def test_entries_survive_new_cache_instances_and_expire(tmp_path, monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr(cache_module.time, "time", lambda: clock[0])
    cache = ResponseCache(tmp_path)
    cache.set("query", {"events": []})
    reopened = ResponseCache(tmp_path)
    assert reopened.get("query", ttl=10).data == {"events": []}
    assert reopened.get("query", ttl=10).fetched_at == 1000
    clock[0] += 10
    assert reopened.get("query", ttl=10) is None


@pytest.mark.parametrize("damage", ["json", "hash", "version"])
def test_corrupt_entries_are_misses(tmp_path, damage):
    cache = ResponseCache(tmp_path)
    cache.set("query", {"score": 0})
    path = next(cache.directory.glob("*.json"))
    if damage == "json":
        path.write_text("invalid", encoding="utf-8")
    else:
        entry = json.loads(path.read_text(encoding="utf-8"))
        if damage == "hash":
            entry["data"]["score"] = 9
        else:
            entry["version"] = 99
        path.write_text(json.dumps(entry), encoding="utf-8")
    assert cache.get("query", ttl=100) is None


def test_failed_replacement_keeps_previous_response(tmp_path, monkeypatch):
    cache = ResponseCache(tmp_path)
    cache.set("query", {"score": 0})
    def fail(*args):
        raise OSError("disk failure")

    monkeypatch.setattr(cache_module.os, "replace", fail)
    with pytest.raises(CacheError, match="disk failure"):
        cache.set("query", {"score": 2})
    assert cache.get("query", ttl=100).data == {"score": 0}
    assert not list(cache.directory.glob("*.tmp"))


def test_clear_only_removes_owned_response_files(tmp_path):
    cache = ResponseCache(tmp_path)
    cache.set("query", {"events": []})
    (cache.directory / "notes.json").write_text("{}", encoding="utf-8")
    assert cache.clear() == 1
    assert (cache.directory / "notes.json").exists()
    assert cache.get("query", ttl=100) is None


def test_policy_distinguishes_live_upcoming_recent_and_historical():
    policy = CachePolicy()
    today = datetime.now(timezone.utc).date()
    finished = {"events": [{"status": {"type": {"completed": True}}}]}
    pending = {"events": [{"status": {"type": {"completed": False}}}]}
    assert policy.scoreboard_ttl(today.isoformat(), finished) == policy.live_ttl
    assert policy.scoreboard_ttl((today + timedelta(days=1)).isoformat(), pending) == policy.upcoming_ttl
    assert policy.scoreboard_ttl((today - timedelta(days=1)).isoformat(), finished) == policy.recent_ttl
    old = (today - timedelta(days=30)).isoformat()
    assert policy.scoreboard_ttl(old, finished) == policy.historical_ttl
    assert policy.scoreboard_ttl(old, pending) == policy.live_ttl
    assert policy.scoreboard_ttl(old, {"events": []}) == policy.historical_ttl


@pytest.mark.parametrize("options", [{"live_ttl": -1}, {"calendar_ttl": float("inf")},
                                     {"recent_days": 1.5}])
def test_invalid_policy_raises(options):
    with pytest.raises(ValueError):
        CachePolicy(**options)


@pytest.mark.parametrize("event", [None, {}, {"status": None}, {"status": {"type": None}},
                                 {"status": {"type": {"completed": "true"}}}])
def test_unknown_event_status_uses_short_ttl_without_crashing(event):
    policy = CachePolicy()
    assert policy.scoreboard_ttl("2024-01-01", {"events": [event]}) == policy.live_ttl

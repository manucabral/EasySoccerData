"""Incremental downloads reuse validated source responses across client instances."""

from copy import deepcopy
from datetime import datetime, timezone
from unittest.mock import Mock
from urllib.parse import parse_qs, urlparse

import pytest

import esd._response_reader as reader_module
import esd.cache as cache_module
import esd.espn.service as service_module
from esd import CachePolicy, DatasetLoadError, ResponseCache, load_dataset
from esd.espn.service import ESPNService
from esd.exceptions import SourceError


def event(identifier, date, score=0):
    return {
        "id": identifier, "date": date, "season": {"year": 2024},
        "status": {"type": {"completed": True}},
        "competitions": [{"competitors": [
            {"homeAway": "home", "team": {"id": "home", "displayName": "Home"}, "score": score},
            {"homeAway": "away", "team": {"id": "away", "displayName": "Away"}, "score": 0},
        ]}],
    }


@pytest.fixture
def source(monkeypatch):
    calendar = ["2024-08-16T07:00Z", "2024-08-17T07:00Z"]
    responses = {
        "20240701": [],
        "20240816": [event("001", "2024-08-16T21:00Z")],
        "20240817": [event("002", "2024-08-17T21:00Z")],
    }
    clock = [datetime.now(timezone.utc).timestamp()]
    monkeypatch.setattr(cache_module.time, "time", lambda: clock[0])

    def fetch(url, **kwargs):
        day = parse_qs(urlparse(url).query)["dates"][0]
        events = responses[day]
        if isinstance(events, Exception):
            raise events
        return {"leagues": [{"slug": "eng.1", "season": {"year": 2024},
                             "calendarType": "day", "calendar": list(calendar)}],
                "events": deepcopy(events)}

    fetcher = Mock(side_effect=fetch)
    monkeypatch.setattr(service_module, "get_api_json", fetcher)
    return fetcher, responses, calendar, clock


def load(tmp_path, **kwargs):
    return load_dataset(source="espn", league="eng.1", season=2024,
                        cache_dir=tmp_path, request_delay=0, **kwargs)


def test_new_loader_reuses_fresh_responses_without_requests(tmp_path, source):
    fetcher, _, _, _ = source
    first = load(tmp_path)
    assert fetcher.call_count == 3
    progress = []
    second = load(tmp_path, progress=progress.append)
    assert fetcher.call_count == 3
    assert second.match_records == first.match_records
    assert second.complete
    assert all(item.cached for item in progress)
    assert second.metadata.response_fetched_at == first.metadata.response_fetched_at
    assert second.metadata.cached_tasks == ("calendar:2024", "matches:2024-08-16", "matches:2024-08-17")


def test_interrupted_download_resumes_only_missing_day(tmp_path, source):
    fetcher, responses, _, _ = source
    original = responses["20240817"]
    responses["20240817"] = SourceError("offline")
    with pytest.raises(DatasetLoadError):
        load(tmp_path)
    assert fetcher.call_count == 3
    responses["20240817"] = original
    progress = []
    result = load(tmp_path, progress=progress.append)
    assert fetcher.call_count == 4
    assert result.complete
    assert len(result.match_records) == 2
    assert [item.cached for item in progress] == [True, True, False]


def test_expired_calendar_discovers_new_day_without_redownloading_old_days(tmp_path, source):
    fetcher, responses, calendar, clock = source
    policy = CachePolicy(calendar_ttl=1)
    load(tmp_path, cache_policy=policy)
    calendar.append("2024-08-18T07:00Z")
    responses["20240818"] = [event("003", "2024-08-18T21:00Z")]
    clock[0] += 2
    result = load(tmp_path, cache_policy=policy)
    assert fetcher.call_count == 5  # Calendar and new day only.
    assert len(result.match_records) == 3
    assert len(result.metadata.successful_dates) == 3


def test_force_refresh_replaces_cached_observations(tmp_path, source):
    fetcher, responses, _, clock = source
    load(tmp_path)
    responses["20240816"] = [event("001", "2024-08-16T21:00Z", score=2)]
    clock[0] += 1
    result = load(tmp_path, refresh=True)
    assert fetcher.call_count == 6
    assert result.match_records[0].home_score == 2
    cached = load(tmp_path)
    assert fetcher.call_count == 6
    assert cached.match_records[0].home_score == 2


def test_old_pending_match_uses_short_ttl(tmp_path, source):
    fetcher, responses, _, clock = source
    responses["20240816"][0]["status"]["type"]["completed"] = False
    load(tmp_path)
    clock[0] += 31
    responses["20240816"][0]["status"]["type"]["completed"] = True
    result = load(tmp_path)
    assert fetcher.call_count == 4
    assert result.complete


def test_newer_duplicate_wins_over_later_day_with_stale_cached_version(tmp_path, source):
    _, responses, _, clock = source
    responses["20240817"] = [event("001", "2024-08-17T21:00Z", score=0)]
    responses["20240816"][0]["status"]["type"]["completed"] = False
    load(tmp_path)
    clock[0] += 31
    responses["20240816"] = [event("001", "2024-08-16T21:00Z", score=3)]
    result = load(tmp_path)
    assert len(result.match_records) == 1
    assert result.match_records[0].home_score == 3
    assert result.match_records[0].kickoff.day == 16


def test_invalid_source_response_is_not_cached(tmp_path, source):
    fetcher, responses, _, _ = source
    responses["20240816"] = [{"date": "2024-08-16T21:00Z"}]
    result = load(tmp_path, on_error="collect")
    assert not result.complete
    responses["20240816"] = [event("001", "2024-08-16T21:00Z")]
    recovered = load(tmp_path)
    assert fetcher.call_count == 4
    assert recovered.complete


def test_rate_limit_delay_applies_to_misses_only(tmp_path, source, monkeypatch):
    monkeypatch.setattr(reader_module.time, "monotonic", lambda: 100.0)
    sleep = Mock()
    monkeypatch.setattr(reader_module.time, "sleep", sleep)
    service = ESPNService(response_cache=ResponseCache(tmp_path), request_delay=0.25)
    service.get_scoreboard("eng.1", "2024-08-16", expected_season=2024)
    service.get_scoreboard("eng.1", "2024-08-16", expected_season=2024)
    sleep.assert_not_called()
    service.get_scoreboard("eng.1", "2024-08-17", expected_season=2024)
    sleep.assert_called_once_with(0.25)

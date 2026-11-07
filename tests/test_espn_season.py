"""Strict source validation prevents incomplete season downloads looking valid."""

from unittest.mock import Mock

import pytest

from esd.espn.service import ESPNService
from esd.exceptions import SourceError


def payload():
    return {"events": [], "leagues": [{
        "slug": "eng.1", "season": {"year": 2024, "displayName": "2024-25"},
        "calendarType": "day",
        "calendar": ["2024-08-17T07:00Z", "2024-08-16T07:00Z", "2024-08-16T07:00Z"],
    }]}


@pytest.fixture
def service():
    service = ESPNService()
    service._fetch = Mock(return_value=payload())
    return service


def test_calendar_dates_are_sorted_and_deduplicated(service):
    calendar = service.get_season_calendar("eng.1", 2024)
    assert calendar.dates == ("2024-08-16", "2024-08-17")
    assert calendar.name == "2024-25"
    assert "dates=20240701" in service._fetch.call_args.args[0]


def test_stage_calendar_ranges_include_boundary_days_and_deduplicate(service):
    data = payload()
    data["leagues"][0].update(calendarType="list", calendar=[{"entries": [
        {"startDate": "2024-06-14T07:00Z", "endDate": "2024-06-15T06:59Z"},
        {"startDate": "2024-06-15T07:00Z", "endDate": "2024-06-16T06:59Z"},
    ]}])
    service._fetch.return_value = data
    calendar = service.get_season_calendar("eng.1", 2024)
    assert calendar.calendar_type == "list"
    assert calendar.dates == ("2024-06-14", "2024-06-15", "2024-06-16")


@pytest.mark.parametrize("data", [
    {}, {"events": []},
    {"leagues": [{"slug": "eng.1", "season": {"year": 2023}}]},
    {"leagues": [{"slug": "other", "season": {"year": 2024}}]},
])
def test_missing_or_wrong_season_raises(service, data):
    service._fetch.return_value = data
    with pytest.raises(SourceError):
        service.get_season_calendar("eng.1", 2024)


@pytest.mark.parametrize("calendar, kind", [([], "day"), (["invalid"], "day"),
                                                    ([{}], "list"), ([{}], "day")])
def test_unusable_calendar_raises(service, calendar, kind):
    data = payload()
    data["leagues"][0].update(calendar=calendar, calendarType=kind)
    service._fetch.return_value = data
    with pytest.raises(SourceError):
        service.get_season_calendar("eng.1", 2024)


def test_strict_scoreboard_distinguishes_empty_day_and_missing_payload(service):
    assert service.get_scoreboard("eng.1", "2024-08-16", expected_season=2024) == []
    assert "limit=1000" in service._fetch.call_args.args[0]
    data = payload()
    del data["events"]
    service._fetch.return_value = data
    with pytest.raises(SourceError, match="events list"):
        service.get_scoreboard("eng.1", "2024-08-16", expected_season=2024)
    service._fetch.return_value = {}
    assert service.get_scoreboard("eng.1", "2024-08-16") == []


def test_strict_scoreboard_rejects_potential_truncation(service):
    data = payload()
    data["events"] = [{}] * 1000
    service._fetch.return_value = data
    with pytest.raises(SourceError, match="truncated"):
        service.get_scoreboard("eng.1", "2024-08-16", expected_season=2024)


def test_strict_scoreboard_rejects_events_from_another_season(service):
    data = payload()
    data["events"] = [{"id": "001", "season": {"year": 2023}}]
    service._fetch.return_value = data
    with pytest.raises(SourceError, match="another season"):
        service.get_scoreboard("eng.1", "2024-08-16", expected_season=2024)


@pytest.mark.parametrize("data", [{}, {"children": [], "season": {"year": 2023}}])
def test_strict_standings_reject_missing_or_wrong_season(service, data):
    service._fetch.return_value = data
    with pytest.raises(SourceError):
        service.get_standings("eng.1", 2024, strict=True)


def test_strict_standings_accept_explicit_empty_tables(service):
    service._fetch.return_value = {"children": [], "season": {"year": 2024}}
    assert service.get_standings("eng.1", 2024, strict=True) == []

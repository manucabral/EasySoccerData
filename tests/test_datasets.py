"""Season downloads expose coverage and failures without external requests."""

from unittest.mock import Mock

import pytest

import esd.datasets as datasets
from esd import DatasetLoadError, load_dataset
from esd.espn.types import (
    ESPNMatch,
    ESPNSeasonCalendar,
    ESPNStandingRow,
    ESPNStandingTable,
    ESPNTeam,
)
from esd.exceptions import SourceBlocked, SourceError

DATES = ("2024-08-16", "2024-08-17")


@pytest.fixture
def client(monkeypatch):
    client = Mock()
    client.get_season_calendar.return_value = ESPNSeasonCalendar("eng.1", 2024, DATES)
    client.get_scoreboard.return_value = []
    client.get_standings.return_value = []
    factory = Mock(return_value=client)
    monkeypatch.setattr(datasets, "ESPNClient", factory)
    client.factory = factory
    return client


def match(identifier="001", score=0):
    return ESPNMatch(id=identifier, date="2024-08-16T21:00Z",
                     home_team=ESPNTeam(id="001", name="Home", score=score),
                     away_team=ESPNTeam(id="002", name="Away"))


def test_season_deduplicates_matches_and_retains_coverage(client):
    client.get_scoreboard.side_effect = [[match()], [match(score=2), match("002")]]
    client.get_standings.return_value = [ESPNStandingTable(id="A", rows=[
        ESPNStandingRow(team=ESPNTeam(id="001"), points=3),
    ])]
    progress = []
    proxies = {"https": "http://proxy.test"}
    result = load_dataset(source="espn", league="eng.1", season=2024,
                          tables=["matches", "standings"], proxies=proxies, progress=progress.append)
    assert result.complete
    assert [row.match_id for row in result.match_records] == ["001", "002"]
    assert result.match_records[0].home_score == 2
    assert len(result.team_records) == 2
    assert result.standing_records[0].table_id == "A"
    assert result.metadata.calendar_dates == result.metadata.successful_dates == DATES
    assert result.metadata.tables == ("matches", "standings", "teams")
    assert result.metadata.started_at <= result.metadata.finished_at
    assert result.metadata.started_at.utcoffset().total_seconds() == 0
    assert result.errors == ()
    assert [event.completed for event in progress] == [1, 2, 3, 4]
    assert all(event.total == 4 for event in progress)
    assert progress[-1].match_count == 2
    assert client.factory.call_args.kwargs["proxies"] == proxies
    assert client.factory.call_args.kwargs["request_delay"] == 0.25
    client.get_season_calendar.assert_called_once_with("eng.1", 2024, anchor_date=None)
    assert client.get_scoreboard.call_args_list[0].kwargs == {"expected_season": 2024}
    client.get_standings.assert_called_once_with("eng.1", 2024, strict=True)


def test_collect_mode_preserves_failed_day_and_keeps_downloading(client):
    client.get_scoreboard.side_effect = [SourceBlocked("blocked"), [match()]]
    progress = []
    result = load_dataset(source="espn", league="eng.1", season="2024",
                          on_error="collect", progress=progress.append)
    assert not result.complete
    assert len(result.match_records) == 1
    assert result.metadata.successful_dates == (DATES[1],)
    assert result.errors[0].target == DATES[0]
    assert result.errors[0].error_type == "SourceBlocked"
    assert [event.success for event in progress] == [True, False, True]


def test_raise_mode_attaches_partial_result_and_stops(client):
    error = SourceError("unavailable")
    client.get_scoreboard.side_effect = [[match()], error]
    with pytest.raises(DatasetLoadError) as caught:
        load_dataset(source="espn", league="eng.1", season=2024, tables=["matches", "standings"])
    result = caught.value.dataset
    assert caught.value.__cause__ is error
    assert not result.complete
    assert len(result.match_records) == 1
    assert result.metadata.successful_dates == (DATES[0],)
    assert result.errors[0].target == DATES[1]
    client.get_standings.assert_not_called()


def test_bad_match_marks_entire_day_failed_without_committing_partial_batch(client):
    client.get_scoreboard.side_effect = [[match(), match(identifier=None)], []]
    result = load_dataset(source="espn", league="eng.1", season=2024, on_error="collect")
    assert not result.complete
    assert not result.match_records
    assert not result.team_records
    assert result.metadata.successful_dates == (DATES[1],)
    assert result.errors[0].step == "matches"


def test_calendar_failure_is_not_a_successful_empty_season(client):
    client.get_season_calendar.side_effect = SourceError("no calendar")
    result = load_dataset(source="espn", league="eng.1", season=2024, on_error="collect",
                          tables=["matches", "standings"])
    assert not result.complete
    assert not result.metadata.calendar_loaded
    assert result.errors[0].step == "calendar"
    assert result.metadata.standings_loaded
    client.get_scoreboard.assert_not_called()


def test_standings_failure_keeps_matches(client):
    client.get_standings.side_effect = SourceError("no standings")
    result = load_dataset(source="espn", league="eng.1", season=2024, on_error="collect",
                          tables=["matches", "standings"])
    assert not result.complete
    assert result.metadata.successful_dates == DATES
    assert not result.metadata.standings_loaded
    assert result.errors[0].step == "standings"


def test_standings_only_does_not_download_matches(client):
    result = load_dataset(source="espn", league="eng.1", season=2024, tables=["standings"])
    assert result.complete
    client.get_season_calendar.assert_not_called()
    client.get_scoreboard.assert_not_called()
    with pytest.raises(ValueError, match="not requested"):
        _ = result.matches


def test_callback_exception_propagates_without_becoming_source_failure(client):
    def progress(event):
        raise RuntimeError("callback failed")

    with pytest.raises(RuntimeError, match="callback failed"):
        load_dataset(source="espn", league="eng.1", season=2024,
                     on_error="collect", progress=progress)
    client.get_scoreboard.assert_not_called()


def test_anchor_date_is_forwarded_and_zero_delay_does_not_sleep(client):
    load_dataset(source="espn", league="eng.1", season=2024,
                 anchor_date="2024-08-01", request_delay=0)
    client.get_season_calendar.assert_called_once_with("eng.1", 2024, anchor_date="2024-08-01")
    assert client.factory.call_args.kwargs["request_delay"] == 0


@pytest.mark.parametrize("populated", [False, True])
def test_dataset_dataframe_tables_have_stable_types(client, populated):
    pd = pytest.importorskip("pandas")
    if populated:
        client.get_scoreboard.return_value = [match()]
    result = load_dataset(source="espn", league="eng.1", season=2024,
                          tables=["matches", "standings"])
    assert str(result.matches["home_score"].dtype) == "Int64"
    assert str(result.matches["kickoff"].dtype) == "datetime64[ns, UTC]"
    assert str(result.teams["team_id"].dtype) == "string"
    assert str(result.standings["points"].dtype) == "Int64"
    if populated:
        assert len(result.matches) == 1
        assert result.matches.loc[0, "home_score"] == 0
        assert pd.isna(result.matches.loc[0, "away_score"])
        assert result.teams["team_id"].tolist() == ["001", "002"]


@pytest.mark.parametrize("kwargs", [
    {"source": "other"}, {"league": "all"}, {"league": ""}, {"season": "2024-25"},
    {"season": True}, {"tables": []}, {"tables": "matches"}, {"tables": ["unknown"]},
    {"tables": ["teams"]}, {"on_error": "ignore"}, {"request_delay": -1},
    {"request_delay": float("nan")},
    {"cache_policy": "invalid"}, {"cache_policy": datasets.CachePolicy()}, {"refresh": "yes"},
])
def test_invalid_options_do_not_start_requests(client, kwargs):
    options = {"source": "espn", "league": "eng.1", "season": 2024, **kwargs}
    with pytest.raises(ValueError):
        load_dataset(**options)
    client.factory.assert_not_called()

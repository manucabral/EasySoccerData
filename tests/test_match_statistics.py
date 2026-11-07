"""Bounded native-ID detail downloads, nullable statistics and source validation."""

import subprocess
import sys
from copy import deepcopy
from dataclasses import replace
from unittest.mock import Mock

import pytest

import esd
from esd import _provider_datasets


def espn_payload(identifier="1"):
    return {"header": {"id": identifier, "league": {"slug": "test.cup"}, "season": {"year": 2026},
                       "competitions": [{"id": identifier, "date": "2026-11-03T20:00:00Z", "competitors": [
                           {"homeAway": "home", "team": {"id": "10", "displayName": "Home"}},
                           {"homeAway": "away", "team": {"id": "20", "displayName": "Away"}},
                       ]}]},
            "boxscore": {"teams": [
                {"team": {"id": "20"}, "statistics": [{"name": "totalShots", "displayValue": "4"}]},
                {"team": {"id": "10"}, "statistics": [
                    {"name": "possessionPct", "displayValue": "51.5"},
                    {"name": "totalShots", "displayValue": "12"},
                    {"name": "redCards", "displayValue": "0"},
                ]},
            ]}}


def scores_payload(identifier=1):
    return {"games": [{"id": identifier, "competitionId": 72, "sportId": 1, "seasonNum": 228,
                       "startTime": "2026-11-03T20:00:00Z", "statusGroup": 4,
                       "homeCompetitor": {"id": 10, "name": "Home"}, "awayCompetitor": {"id": 20, "name": "Away"}}],
            "actualGameStatistics": {"filterId": -1}, "statistics": [
                {"id": 3, "competitorId": 20, "value": "4", "valuePercentage": 0.25},
                {"id": 3, "competitorId": 10, "value": "12", "valuePercentage": 0.75},
                {"id": 10, "competitorId": 10, "value": "51.5%", "valuePercentage": 0.515},
                {"id": 2, "competitorId": 10, "value": "0"},
                {"id": 76, "competitorId": 10, "value": "1.23"},
                {"id": 999, "value": "An unsupported metric"},
            ]}


def sofa_event(identifier=1):
    return {"event": {"id": identifier, "season": {"id": 228},
                      "tournament": {"uniqueTournament": {"id": 72}},
                      "startTimestamp": 1793736000, "status": {"type": "finished"},
                      "homeTeam": {"id": 10, "name": "Home"}, "awayTeam": {"id": 20, "name": "Away"},
                      "homeScore": {"current": 1}, "awayScore": {"current": 0}}}


def sofa_stats():
    return {"statistics": [
        {"period": "1ST", "groups": [{"statisticsItems": [{"key": "totalShotsOnGoal", "homeValue": 7, "awayValue": 3}]}]},
        {"period": "ALL", "groups": [{"statisticsItems": [
            {"key": "totalShotsOnGoal", "homeValue": 12, "awayValue": 4},
            {"key": "ballPossession", "homeValue": 51.5},
            {"key": "redCards", "homeValue": 0},
        ]}]},
    ]}


@pytest.fixture
def fetch(monkeypatch):
    fetch = Mock()
    monkeypatch.setattr(_provider_datasets, "get_api_json", fetch)
    return fetch


def load(source="espn", **options):
    query = {"source": source, "league": "test.cup" if source == "espn" else 72,
             "season": 2026, "tables": ["match_stats"], "match_ids": [1], "request_delay": 0}
    if source != "espn":
        query["season_id"] = 228
    return esd.load_dataset(**(query | options))


@pytest.mark.parametrize("source,payload,calls", [("espn", espn_payload(), 1), ("scores365", scores_payload(), 1), ("sofascore", None, 2)])
def test_details_have_explicit_scope_native_identity_and_nullable_counts(fetch, source, payload, calls):
    fetch.side_effect = [sofa_event(), sofa_stats()] if source == "sofascore" else [deepcopy(payload)]
    dataset = load(source)
    assert dataset.complete and esd.validate_dataset(dataset).valid
    assert set(dataset.metadata.tables) == {"match_stats", "matches", "teams"}
    assert dataset.metadata.coverage_scope == "match_ids" and dataset.metadata.requested_match_ids == ("1",)
    assert len(dataset.match_records) == len(dataset.match_stat_records) == 1
    stats = dataset.match_stat_records[0]
    assert (stats.home_shots, stats.away_shots, stats.home_red_cards) == (12, 4, 0)
    assert stats.home_possession_pct == 51.5
    assert stats.away_red_cards is None and stats.home_saves is None
    assert stats.forecast_win is None
    assert fetch.call_count == calls
    assert all("scoreboard" not in call.args[0] and "/events/" not in call.args[0] for call in fetch.call_args_list)
    assert len(dataset.metadata.successful_tasks) == len(dataset.metadata.expected_tasks) == calls


@pytest.mark.parametrize("options", [
    {"match_ids": None}, {"match_ids": []}, {"match_ids": "1"}, {"match_ids": [True]},
    {"match_ids": [-1]}, {"match_ids": ["١"]}, {"match_ids": [1, 2], "max_match_requests": 1},
    {"max_match_requests": True}, {"max_match_requests": 0},
    {"start_date": "2026-11-03", "end_date": "2026-11-03"},
    {"anchor_date": "2026-11-03"}, {"tables": ["match_stats", "standings"]}, {"season_id": 228},
])
def test_bad_selection_and_budget_are_rejected_before_network(fetch, options):
    with pytest.raises(ValueError):
        load(**options)
    fetch.assert_not_called()


def test_sofascore_budget_counts_context_and_stats_before_requests(fetch):
    with pytest.raises(ValueError, match="2 endpoint reads"):
        load("sofascore", max_match_requests=1)
    fetch.assert_not_called()


@pytest.mark.parametrize("source", ["scores365", "sofascore"])
def test_native_season_is_required_before_network(fetch, source):
    with pytest.raises(ValueError):
        load(source, season_id=None)
    fetch.assert_not_called()


def test_duplicate_ids_do_not_repeat_detail_requests(fetch):
    fetch.return_value = espn_payload()
    dataset = load(match_ids=["001", 1, "1"], max_match_requests=1)
    assert dataset.metadata.requested_match_ids == ("1",) and fetch.call_count == 1


@pytest.mark.parametrize("change", ["event", "league", "season", "missing_teams", "unknown_team", "contradictory_side", "invalid_count", "duplicate_metric"])
def test_espn_identity_and_statistic_errors_never_publish_cache(fetch, tmp_path, change):
    data = espn_payload()
    if change == "event":
        data["header"]["id"] = "2"
    elif change == "league":
        data["header"]["league"]["slug"] = "other.cup"
    elif change == "season":
        data["header"]["season"]["year"] = 2025
    elif change == "missing_teams":
        data["boxscore"].pop("teams")
    elif change == "unknown_team":
        data["boxscore"]["teams"][0]["team"]["id"] = "999"
    elif change == "contradictory_side":
        data["boxscore"]["teams"][0]["homeAway"] = "home"
    elif change == "invalid_count":
        data["boxscore"]["teams"][0]["statistics"][0]["displayValue"] = "4/9"
    else:
        data["boxscore"]["teams"][0]["statistics"].append({"name": "totalShots", "displayValue": "5"})
    fetch.return_value = data
    result = load(cache_dir=tmp_path, on_error="collect")
    assert not result.complete and not result.match_stat_records
    assert result.errors[0].error_type == "SourceError"
    assert not list(tmp_path.rglob("*.json"))


@pytest.mark.parametrize("field,value", [("competitionId", 99), ("seasonNum", 999), ("id", 2), ("sportId", True)])
def test_scores_stat_response_requires_its_selected_match_context(fetch, field, value):
    data = scores_payload()
    data["games"][0][field] = value
    fetch.return_value = data
    with pytest.raises(esd.DatasetLoadError):
        load("scores365")


def test_scores_percentages_and_xg_are_not_ratios_of_other_statistics(fetch):
    fetch.return_value = scores_payload()
    row = load("scores365").match_stat_records[0]
    assert row.home_possession_pct == 51.5 and row.home_shots == 12 and row.home_xg == 1.23
    assert row.away_possession_pct is None


@pytest.mark.parametrize("change", ["team", "period", "missing_list", "boolean_id"])
def test_scores_rejects_unknown_teams_periods_and_malformed_statistics(fetch, change):
    data = scores_payload()
    if change == "team":
        data["statistics"][0]["competitorId"] = 999
    elif change == "period":
        data["actualGameStatistics"]["filterId"] = 6
    elif change == "missing_list":
        data.pop("statistics")
    else:
        data["statistics"][0]["id"] = True
    fetch.return_value = data
    result = load("scores365", on_error="collect")
    assert not result.complete and result.errors[0].error_type == "SourceError"


def test_missing_scores_period_metadata_stays_unknown(fetch):
    data = scores_payload()
    data.pop("actualGameStatistics")
    fetch.return_value = data
    assert load("scores365").match_stat_records[0].source_period is None


@pytest.mark.parametrize("source", ["espn", "scores365", "sofascore"])
def test_explicit_empty_statistics_preserve_null_metrics(fetch, source):
    if source == "espn":
        data = espn_payload()
        data["boxscore"]["teams"] = []
    elif source == "scores365":
        data = scores_payload()
        data["statistics"] = []
    else:
        fetch.side_effect = [sofa_event(), {"statistics": []}]
        data = None
    fetch.return_value = data
    row = load(source).match_stat_records[0]
    assert row.home_shots is row.away_shots is row.home_possession_pct is row.home_xg is None


@pytest.mark.parametrize("change", ["no_all", "two_all", "invalid_value", "conflict"])
def test_sofascore_never_sums_periods_or_uses_conflicting_totals(fetch, change):
    data = sofa_stats()
    if change == "no_all":
        data["statistics"].pop()
    elif change == "two_all":
        data["statistics"].append(deepcopy(data["statistics"][-1]))
    else:
        items = data["statistics"][-1]["groups"][0]["statisticsItems"]
        if change == "invalid_value":
            items[0]["homeValue"] = -1
        else:
            items.append({"key": "totalShotsOnGoal", "homeValue": 999, "awayValue": 4})
    fetch.side_effect = [sofa_event(), data]
    result = load("sofascore", on_error="collect")
    assert not result.complete and len(result.match_records) == 1 and not result.match_stat_records
    assert result.errors[0].step == "match_stats"


def test_sofascore_context_failure_does_not_fetch_statistics(fetch):
    event = sofa_event()
    event["event"]["season"]["id"] = 999
    fetch.return_value = event
    result = load("sofascore", on_error="collect")
    assert fetch.call_count == 1 and not result.complete
    assert {issue.step for issue in result.errors} == {"match", "match_stats"}


def test_cache_provenance_failed_refresh_and_source_proxy_forwarding(fetch, tmp_path):
    fetch.return_value = espn_payload()
    options = {"cache_dir": tmp_path, "proxies": {"https": "http://proxy.test"}}
    first = load(**options)
    second = load(**options)
    assert first.match_stat_records == second.match_stat_records and fetch.call_count == 1
    assert second.metadata.cached_tasks == ("match_stats:1",)
    assert second.metadata.response_fetched_at == first.metadata.response_fetched_at
    assert fetch.call_args.kwargs["proxies"] is options["proxies"]
    fetch.return_value = {}
    failed = load(**options, refresh=True, on_error="collect")
    assert not failed.complete and fetch.call_count == 2
    recovered = load(**options)
    assert recovered.complete and recovered.match_stat_records == first.match_stat_records
    assert fetch.call_count == 2


def test_collect_and_raise_preserve_partial_records_and_progress(fetch):
    fetch.side_effect = [espn_payload(), esd.SourceBlocked("Example block")]
    progress = []
    result = load(match_ids=[1, 2], on_error="collect", progress=progress.append)
    assert not result.complete and len(result.match_stat_records) == 1
    assert result.metadata.requested_match_ids == ("1", "2")
    assert result.errors[0].target == "2" and result.errors[0].error_type == "SourceBlocked"
    assert [event.completed for event in progress] == [1, 2] and progress[-1].total == 2
    fetch.side_effect = [espn_payload(), esd.SourceBlocked("Example block")]
    with pytest.raises(esd.DatasetLoadError) as exc:
        load(match_ids=[1, 2])
    assert len(exc.value.dataset.match_records) == 1


def test_optional_imports_and_browser_are_not_required():
    code = '''
import importlib.abc, sys
class NoExtras(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in ('pandas', 'pyarrow'):
            raise ModuleNotFoundError('Blocked optional import', name=fullname)
sys.meta_path.insert(0, NoExtras())
import esd
from unittest.mock import patch
payload = PAYLOAD
with patch('esd._provider_datasets.get_api_json', return_value=payload), patch('esd.utils.BrowserSession._launch', side_effect=AssertionError('Unexpected browser')):
    dataset = esd.load_dataset(source='espn', league='test.cup', season=2026, tables=['match_stats'], match_ids=[1])
    assert dataset.match_stat_records[0].home_shots == 12
assert 'pandas' not in sys.modules and 'pyarrow' not in sys.modules
'''.replace("PAYLOAD", repr(espn_payload()))
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr


def test_parquet_and_dataframes_keep_nulls_counts_and_scope(fetch, tmp_path):
    pytest.importorskip("pyarrow")
    fetch.return_value = espn_payload()
    dataset = load()
    restored = esd.open_dataset(dataset.save(tmp_path / "stats"))
    assert restored == dataset
    pd = pytest.importorskip("pandas")
    frame = restored.match_stats
    assert str(frame.home_shots.dtype) == "Int64" and str(frame.home_possession_pct.dtype) == "Float64"
    assert pd.isna(frame.home_saves.iloc[0]) and frame.home_red_cards.iloc[0] == 0


@pytest.mark.parametrize("field,value", [("home_possession_pct", 101), ("away_shots", -1)])
def test_validation_reports_invalid_metrics(fetch, field, value):
    fetch.return_value = espn_payload()
    dataset = load()
    invalid = replace(dataset, match_stat_records=(replace(dataset.match_stat_records[0], **{field: value}),))
    assert "invalid_match_metric" in {issue.code for issue in esd.validate_dataset(invalid).errors}


def test_validation_detects_records_outside_match_id_selection(fetch):
    fetch.return_value = espn_payload()
    dataset = load()
    invalid = replace(dataset, metadata=replace(dataset.metadata, requested_match_ids=("2",)))
    assert "unrequested_match" in {issue.code for issue in esd.validate_dataset(invalid).errors}

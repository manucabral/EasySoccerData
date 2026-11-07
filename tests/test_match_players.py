"""Match-player records preserve roles, identifiers and observed metrics only."""

from copy import deepcopy
from dataclasses import replace
from unittest.mock import Mock

import pytest

import esd
from esd import _provider_datasets


def espn_payload(identifier="1"):
    return {"header": {"id": identifier, "league": {"slug": "test.cup"}, "season": {"year": 2026},
                       "competitions": [{"id": identifier, "date": "2026-11-03T20:00:00Z", "competitors": [
                           {"homeAway": "home", "team": {"id": "10"}}, {"homeAway": "away", "team": {"id": "20"}},
                       ]}]}, "rosters": [
                           {"team": {"id": "20"}, "homeAway": "away", "formation": "4-3-3", "roster": [
                               {"athlete": {"id": "202", "displayName": "Same name"}, "starter": False},
                           ]},
                           {"team": {"id": "10"}, "homeAway": "home", "formation": "4-4-2", "roster": [
                               {"athlete": {"id": "101", "displayName": "Same name"}, "starter": True,
                                "jersey": "01", "stats": [{"name": "totalGoals", "value": 0},
                                                           {"name": "appearances", "value": 1},
                                                           {"name": "totalShots", "value": 3},
                                                           {"name": "shotsOnTarget", "value": 2}]},
                               {"athlete": {"id": "102"}},
                           ]},
                       ], "boxscore": {"teams": []}}


def scores_payload(identifier=1):
    return {"game": {"id": identifier, "competitionId": 72, "seasonNum": 228, "sportId": 1,
                     "startTime": "2026-11-03T20:00:00+00:00", "hasLineups": True,
                     "members": [{"id": 101, "athleteId": 777, "competitorId": 10, "name": "Player", "jerseyNumber": 7}],
                     "homeCompetitor": {"id": 10, "lineups": {"status": "Localized status", "formation": "4-4-2", "members": [
                         {"id": 101, "status": 1, "ranking": 0, "stats": [
                             {"type": 30, "value": "75'"}, {"type": 19, "value": "13/20 (65%)"},
                             {"type": 27, "value": "0"}, {"type": 76, "value": "0.2"},
                         ]}, {"id": 102, "status": 2, "ranking": -1},
                         {"id": 103, "status": 3}, {"id": 104, "status": 4},
                     ]}}, "awayCompetitor": {"id": 20, "lineups": {"members": []}}}}


def sofa_event(identifier=1):
    return {"event": {"id": identifier, "season": {"id": 228},
                      "tournament": {"uniqueTournament": {"id": 72}}, "startTimestamp": 1793736000,
                      "homeTeam": {"id": 10}, "awayTeam": {"id": 20}}}


def sofa_payload():
    return {"confirmed": False, "home": {"formation": "4-4-2", "players": [
        {"player": {"id": 101, "name": "Player", "position": "F"}, "teamId": 10,
         "substitute": False, "captain": True, "shirtNumber": 7,
         "statistics": {"minutesPlayed": 75, "goals": 0, "totalPass": 20, "accuratePass": 13, "rating": 0}},
        {"player": {"id": 102}, "substitute": True}, {"player": {"id": 103}},
    ], "missingPlayers": [{"player": {"id": 104}}]}, "away": {"players": []}}


def load(source="espn", **options):
    query = {"source": source, "league": "test.cup" if source == "espn" else 72,
             "season": 2026, "tables": ["player_match_stats"], "match_ids": [1], "request_delay": 0}
    if source != "espn":
        query["season_id"] = 228
    return esd.load_dataset(**(query | options))


@pytest.fixture
def fetch(monkeypatch):
    fetch = Mock()
    monkeypatch.setattr(_provider_datasets, "get_api_json", fetch)
    return fetch


@pytest.mark.parametrize("source,calls", [("espn", 1), ("scores365", 1), ("sofascore", 2)])
def test_bounded_native_player_downloads_have_explicit_tables_and_nullable_metrics(fetch, source, calls):
    fetch.side_effect = {"espn": [espn_payload()], "scores365": [scores_payload()],
                         "sofascore": [sofa_event(), sofa_payload()]}[source]
    dataset = load(source, max_match_requests=calls)
    assert dataset.complete and esd.validate_dataset(dataset).valid
    assert set(dataset.metadata.tables) == {"lineups", "player_match_stats", "matches", "teams"}
    assert dataset.metadata.coverage_scope == "match_ids" and dataset.metadata.requested_match_ids == ("1",)
    assert len(dataset.match_records) == 1 and len(dataset.player_match_stat_records) == 1
    assert fetch.call_count == calls
    assert len(dataset.metadata.expected_tasks) == len(dataset.metadata.successful_tasks) == calls
    observed = dataset.player_match_stat_records[0]
    assert observed.goals == 0 and observed.player_id == "101"
    assert observed.minutes == (None if source == "espn" else 75)
    assert observed.source_rating == (None if source == "espn" else 0.0)
    unknown = next(row for row in dataset.lineup_records if row.player_id == "102")
    assert unknown.starter is (None if source == "espn" else False)
    assert all(row.player_id != "104" for row in dataset.lineup_records)
    if source == "scores365":
        assert "timezoneName=UTC" in fetch.call_args.args[0]
        assert observed.source_athlete_id == "777" and observed.passes == 20 and observed.accurate_passes == 13
        assert dataset.lineup_records[0].source_lineup_status == "Localized status"
        assert dataset.lineup_records[0].confirmed is None
    elif source == "sofascore":
        assert dataset.lineup_records[0].confirmed is False
    else:
        assert dataset.lineup_records[0].team_id == "20" and observed.team_id == "10"
        assert dataset.lineup_records[1].jersey_number == "01"


def test_public_adapter_preserves_input_and_can_skip_unselected_statistics(fetch):
    raw = espn_payload()
    original = deepcopy(raw)
    fetch.return_value = raw
    dataset = load()
    match = dataset.match_records[0]
    records = esd.normalize_match_players(raw, match=match)
    assert records.lineups == dataset.lineup_records and raw == original
    raw["rosters"][1]["roster"][0]["stats"][0]["value"] = "broken"
    assert esd.normalize_match_players(raw, match=match, include_statistics=False).lineups == records.lineups
    with pytest.raises(esd.SourceError):
        esd.normalize_match_players(raw, match=match)


@pytest.mark.parametrize("source,cost", [("espn", 1), ("scores365", 2), ("sofascore", 3)])
def test_combined_team_and_player_statistics_share_only_compatible_responses(fetch, source, cost):
    if source == "espn":
        fetch.side_effect = [espn_payload()]
    elif source == "scores365":
        data = scores_payload()
        fetch.side_effect = [data, {"games": [data["game"]], "statistics": [], "actualGameStatistics": {"filterId": -1}}]
    else:
        fetch.side_effect = [sofa_event(), sofa_payload(), {"statistics": []}]
    dataset = load(source, tables=["player_match_stats", "match_stats"], max_match_requests=cost)
    assert dataset.complete and esd.validate_dataset(dataset).valid and fetch.call_count == cost
    assert len(dataset.match_stat_records) == 1
    if source == "espn":
        report = esd.compare_match_statistics(dataset, dataset, metrics=["home_shots"])
        assert report.rows[0].left_fetched_at is not None


@pytest.mark.parametrize("source,budget", [("scores365", 1), ("sofascore", 2)])
def test_combined_budget_is_checked_before_any_request(fetch, source, budget):
    with pytest.raises(ValueError, match="endpoint reads"):
        load(source, tables=["lineups", "match_stats"], max_match_requests=budget)
    fetch.assert_not_called()


@pytest.mark.parametrize("options", [{"match_ids": []}, {"match_ids": None}, {"match_ids": [True]},
                                      {"start_date": "2026-11-03"}, {"tables": ["lineups", "standings"]},
                                      {"max_match_requests": 0}])
def test_invalid_selection_is_rejected_before_network(fetch, options):
    with pytest.raises(ValueError):
        load(**options)
    fetch.assert_not_called()


@pytest.mark.parametrize("change", ["duplicate", "wrong_team", "wrong_event", "missing_rosters", "bad_flag", "bad_count"])
def test_invalid_players_are_not_cached_or_published(fetch, tmp_path, change):
    data = espn_payload()
    if change == "duplicate":
        data["rosters"][1]["roster"].append(data["rosters"][1]["roster"][0])
    elif change == "wrong_team":
        data["rosters"][0]["team"]["id"] = "999"
    elif change == "wrong_event":
        data["header"]["id"] = "999"
    elif change == "missing_rosters":
        del data["rosters"]
    elif change == "bad_flag":
        data["rosters"][0]["roster"][0]["starter"] = 0
    else:
        data["rosters"][1]["roster"][0]["stats"][0]["value"] = -1
    fetch.return_value = data
    cache = tmp_path / "cache"
    dataset = load(cache_dir=cache, on_error="collect")
    assert not dataset.complete and dataset.errors and not dataset.lineup_records
    assert not dataset.match_records and not list(cache.rglob("*.json"))


@pytest.mark.parametrize("value", ["21/20 (100%)", "13/20 (101%)", "broken/20", True, "NaN"])
def test_invalid_passes_fail_without_substituting_percentages(fetch, value):
    data = scores_payload()
    data["game"]["homeCompetitor"]["lineups"]["members"][0]["stats"][1]["value"] = value
    fetch.return_value = data
    with pytest.raises(esd.DatasetLoadError):
        load("scores365")


def test_partial_sofa_lineup_failure_keeps_context_and_team_statistics(fetch):
    fetch.side_effect = [sofa_event(), esd.SourceBlocked("Source block"), {"statistics": []}]
    dataset = load("sofascore", tables=["player_match_stats", "match_stats"], on_error="collect")
    assert not dataset.complete and len(dataset.match_records) == len(dataset.match_stat_records) == 1
    assert not dataset.lineup_records and not dataset.player_match_stat_records
    assert dataset.errors[0].step == "lineups" and dataset.errors[0].error_type == "SourceBlocked"
    assert esd.validate_dataset(dataset).valid


def test_failed_sofa_context_skips_dependent_endpoints(fetch):
    fetch.side_effect = esd.SourceBlocked("Context block")
    dataset = load("sofascore", tables=["lineups", "match_stats"], on_error="collect")
    assert fetch.call_count == 1 and not dataset.complete and len(dataset.errors) == 3


def test_cache_reuse_retains_both_tables_and_original_task_times(fetch, tmp_path):
    fetch.return_value = espn_payload()
    first = load(cache_dir=tmp_path / "cache")
    second = load(cache_dir=tmp_path / "cache")
    assert fetch.call_count == 1 and first.lineup_records == second.lineup_records
    assert first.player_match_stat_records == second.player_match_stat_records
    assert first.metadata.response_fetched_at == second.metadata.response_fetched_at
    assert second.metadata.cached_tasks == ("match_details:1",)


def test_same_player_across_matches_keeps_separate_lineups_and_observations(fetch):
    fetch.side_effect = [espn_payload("1"), espn_payload("2")]
    dataset = load(match_ids=[1, 2], max_match_requests=2)
    assert dataset.complete and len(dataset.lineup_records) == 6
    assert len(dataset.player_match_stat_records) == 2
    assert {(row.match_id, row.player_id) for row in dataset.player_match_stat_records} == {("1", "101"), ("2", "101")}
    assert esd.validate_dataset(dataset).valid


@pytest.mark.parametrize("version", ["1", "2"])
def test_legacy_manifest_cannot_claim_new_player_tables(fetch, tmp_path, version):
    pytest.importorskip("pyarrow")
    import json
    fetch.return_value = espn_payload()
    path = load().save(tmp_path / "new-tables")
    manifest = path / "manifest.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["metadata"]["schema_version"] = version
    manifest.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(esd.DatasetFormatError, match="require schema version 3"):
        esd.open_dataset(path)


def test_lineups_only_skips_unselected_365_statistics_and_timeline(fetch):
    data = scores_payload()
    data["game"]["homeCompetitor"]["lineups"]["members"][0]["stats"] = "unselected malformed statistics"
    data["game"]["events"] = "unselected malformed timeline"
    original = deepcopy(data)
    fetch.return_value = data
    dataset = load("scores365", tables=["lineups"], max_match_requests=1)
    assert dataset.complete and len(dataset.lineup_records) == 2 and not dataset.player_match_stat_records
    assert data == original
    with pytest.raises(ValueError, match="not requested"):
        _ = dataset.player_match_stats


def test_365_stats_with_conflicting_context_leave_valid_lineups_and_no_bad_cache(fetch, tmp_path):
    data = scores_payload()
    game = deepcopy(data["game"])
    game["startTime"] = "2026-11-03T21:00:00+00:00"
    fetch.side_effect = [data, {"games": [game], "statistics": []}]
    dataset = load("scores365", tables=["player_match_stats", "match_stats"],
                   cache_dir=tmp_path / "cache", on_error="collect")
    assert not dataset.complete and dataset.lineup_records and not dataset.match_stat_records
    assert dataset.errors[0].step == "match_stats"
    assert len(list((tmp_path / "cache").rglob("*.json"))) == 1
    assert esd.validate_dataset(dataset).valid


def test_lineup_ids_deduplicate_before_budget_and_failed_refresh_preserves_cache(fetch, tmp_path):
    fetch.return_value = espn_payload()
    first = load(match_ids=[1, "01", 1], max_match_requests=1, cache_dir=tmp_path / "cache")
    fetch.side_effect = esd.SourceBlocked("Refresh blocked")
    failed = load(cache_dir=tmp_path / "cache", refresh=True, on_error="collect")
    assert not failed.complete and not failed.lineup_records
    fetch.side_effect = AssertionError("Expected valid original response")
    reused = load(cache_dir=tmp_path / "cache")
    assert reused.lineup_records == first.lineup_records and reused.complete
    assert reused.metadata.response_fetched_at == first.metadata.response_fetched_at
    assert fetch.call_count == 2


def test_dataframe_types_and_snapshot_roundtrip(fetch, tmp_path):
    pytest.importorskip("pandas")
    pytest.importorskip("pyarrow")
    fetch.return_value = espn_payload()
    dataset = load()
    frame = dataset.lineups
    assert str(frame.starter.dtype) == str(frame.confirmed.dtype) == "boolean"
    assert frame.confirmed.isna().all() and frame.starter.isna().sum() == 1
    assert str(dataset.player_match_stats.goals.dtype) == "Int64" and str(dataset.player_match_stats.xg.dtype) == "Float64"
    assert dataset.player_match_stats.minutes.isna().all()
    restored = esd.open_dataset(dataset.save(tmp_path / "players"))
    assert restored == dataset and esd.validate_dataset(restored).valid
    empty = esd.normalized_to_dataframe([], table="lineups")
    assert empty.dtypes.equals(frame.dtypes)


@pytest.mark.parametrize("change,code", [("negative", "invalid_player_metric"), ("foreign_team", "player_team_mismatch"),
                                         ("bad_side", "invalid_lineup_side"), ("duplicate", "duplicate_key"),
                                         ("unrequested", "unrequested_match"), ("two_teams", "player_team_conflict"),
                                         ("cross_table_team", "player_team_conflict")])
def test_validation_checks_player_scope_keys_metrics_and_membership(fetch, change, code):
    fetch.return_value = espn_payload()
    dataset = load()
    lineup = dataset.lineup_records[1]
    stat = dataset.player_match_stat_records[0]
    if change == "negative":
        dataset = replace(dataset, player_match_stat_records=(replace(stat, minutes=-1),))
    elif change == "foreign_team":
        dataset = replace(dataset, lineup_records=(replace(lineup, team_id="999"),))
    elif change == "bad_side":
        dataset = replace(dataset, lineup_records=(replace(lineup, home_away="left"),))
    elif change == "duplicate":
        dataset = replace(dataset, lineup_records=(lineup, lineup))
    elif change == "unrequested":
        dataset = replace(dataset, player_match_stat_records=(replace(stat, match_id="999"),))
    elif change == "cross_table_team":
        dataset = replace(dataset, player_match_stat_records=(replace(stat, team_id="20"),))
    else:
        dataset = replace(dataset, lineup_records=(lineup, replace(lineup, team_id="20", home_away="away")))
    assert code in {item.code for item in esd.validate_dataset(dataset).errors}


def test_legacy_v2_snapshot_keeps_values_provenance_and_empty_new_tables(fetch, tmp_path):
    pytest.importorskip("pyarrow")
    import json
    fetch.return_value = espn_payload()
    dataset = load(tables=["match_stats"])
    path = dataset.save(tmp_path / "old")
    manifest = path / "manifest.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["metadata"]["schema_version"] = "2"
    manifest.write_text(json.dumps(data), encoding="utf-8")
    original = manifest.read_bytes()
    restored = esd.open_dataset(path)
    assert restored == dataset and manifest.read_bytes() == original
    assert restored.metadata.schema_version == "4" and not restored.lineup_records and not restored.player_match_stat_records


def test_unsupported_sources_reject_player_tables_before_requests(fetch):
    for source, contract in esd.get_dataset_capabilities().items():
        if source not in ("espn", "scores365", "sofascore"):
            assert "lineups" not in contract.tables and "player_match_stats" not in contract.tables
            with pytest.raises(ValueError):
                load(source)
    fetch.assert_not_called()

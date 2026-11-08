"""Sofascore incidents use verified match context and retain missing observations."""

import hashlib
import json
from copy import deepcopy
from dataclasses import replace
from unittest.mock import Mock

import pytest

import esd
from esd import _provider_datasets
from tests.test_match_players import sofa_event, sofa_payload


def incidents():
    return {"incidents": [
        {"id": 91, "incidentType": "goal", "incidentClass": "regular", "time": 45, "addedTime": 2,
         "timeSeconds": 2700, "isHome": True, "player": {"id": 101, "name": "Player"},
         "assist1": {"id": 102, "name": "Assist"}, "assist2": {"id": 103}, "rescinded": False},
        {"id": 92, "incidentType": "substitution", "time": 67, "isHome": False,
         "playerIn": {"id": 201, "name": "Incoming"}, "playerOut": {"id": 202, "name": "Outgoing"}},
        {"id": 93, "incidentType": "penaltyShootout", "incidentClass": "missed", "time": -1, "sequence": 2,
         "isHome": False},
        {"incidentType": "period", "text": "HT", "time": 45},
        {"id": 94, "incidentType": "card", "incidentClass": "yellow", "time": -1,
         "player": {"name": "Unnamed staff ID"}, "rescinded": True, "reason": "Native reason"},
    ]}


@pytest.fixture
def fetch(monkeypatch):
    fetch = Mock(side_effect=[sofa_event(), incidents()])
    monkeypatch.setattr(_provider_datasets, "get_api_json", fetch)
    return fetch


def load(**options):
    query = {"source": "sofascore", "league": 72, "season": 2026, "season_id": 228,
             "tables": ["match_events"], "match_ids": [1], "max_match_requests": 2, "request_delay": 0}
    return esd.load_dataset(**(query | options))


def test_incident_contract_keeps_native_identity_sides_clocks_and_cancellations(fetch):
    data = incidents()
    before = deepcopy(data)
    dataset = load()
    assert dataset.complete and esd.validate_dataset(dataset).valid and fetch.call_count == 2
    assert dataset.metadata.expected_tasks == ("match:1", "match_events:1")
    assert set(dataset.metadata.tables) == {"matches", "teams", "match_events"}
    assert not dataset.lineup_records and not dataset.player_match_stat_records
    rows = esd.normalize_match_events(data, match=dataset.match_records[0])
    assert rows == dataset.match_event_records and data == before
    goal, sub, penalty, period, card = rows
    assert goal.event_id == "91" and goal.team_id == "10" and goal.player_id == "101"
    assert goal.minute == 45 and goal.added_minute == 2 and goal.clock_seconds == 2700
    assert goal.source_period is None and goal.rescinded is False and goal.scoring_play is None
    assert goal.related_player_id == "102" and goal.related_player_role == "assist"
    assert json.loads(goal.source_participants_json)["assist2"]["id"] == 103
    assert sub.team_id == "20" and sub.player_id == "201" and sub.related_player_id == "202"
    assert sub.player_role == "incoming" and sub.related_player_role == "outgoing"
    assert penalty.is_shootout is True and penalty.minute is None and penalty.source_game_time is None
    assert penalty.source_order == 2 and penalty.event_type == "penalty_missed"
    assert json.loads(penalty.source_details_json)["time"] == -1
    assert period.event_id is None and period.source_order == 3 and period.event_type == "other"
    assert card.minute is None and card.team_id is None and card.player_id is None
    assert card.rescinded is True and card.event_type == "yellow_card"
    assert json.loads(card.source_details_json)["reason"] == "Native reason"
    assert fetch.call_args_list[1].args[0].endswith("/event/1/incidents")


@pytest.mark.parametrize("kind,native_class,expected", [
    ("goal", "regular", "goal"), ("goal", "ownGoal", "own_goal"), ("goal", "penalty", "penalty_scored"),
    ("card", "yellow", "yellow_card"), ("card", "red", "red_card"), ("card", "yellowRed", "second_yellow_card"),
    ("inGamePenalty", "missed", "penalty_missed"), ("inGamePenalty", "saved", "penalty_missed"),
    ("penaltyShootout", "scored", "penalty_scored"), ("penaltyShootout", "future", "other"),
    ("varDecision", "goalNotAwarded", "other"), ("card", "unreviewed", "other"),
])
def test_native_pairs_map_without_reading_free_text(fetch, kind, native_class, expected):
    data = {"incidents": [{"id": 1, "incidentType": kind, "incidentClass": native_class,
                           "text": "A misleading goal / red card / penalty description", "time": 121}]}
    fetch.side_effect = [sofa_event(), data]
    row = load().match_event_records[0]
    assert row.event_type == expected
    assert row.minute == (None if kind == "penaltyShootout" else 121)


@pytest.mark.parametrize("tables,cost", [(["match_events"], 2), (["match_events", "lineups"], 3),
                                       (["match_events", "player_match_stats"], 3),
                                       (["match_events", "match_stats"], 3),
                                       (["match_events", "player_match_stats", "match_stats"], 4)])
def test_selected_tables_share_context_and_have_exact_preflight_budgets(fetch, tables, cost):
    responses = [sofa_event()]
    if set(tables) & {"lineups", "player_match_stats"}:
        responses.append(sofa_payload())
    responses.append(incidents())
    if "match_stats" in tables:
        responses.append({"statistics": []})
    fetch.side_effect = responses
    with pytest.raises(ValueError, match="exceeding"):
        load(tables=tables, max_match_requests=cost - 1)
    fetch.assert_not_called()
    dataset = load(tables=tables, max_match_requests=cost)
    assert dataset.complete and esd.validate_dataset(dataset).valid and fetch.call_count == cost
    assert [call.args[0].endswith("/event/1") for call in fetch.call_args_list].count(True) == 1


@pytest.mark.parametrize("damage", ["missing_list", "null_list", "duplicate_id", "side", "rescinded",
                                    "time", "context", "foreign_team", "side_conflict", "native_type"])
def test_invalid_incidents_fail_without_publishing_cache(fetch, tmp_path, damage):
    data = incidents()
    first = data["incidents"][0]
    if damage == "missing_list":
        del data["incidents"]
    elif damage == "null_list":
        data["incidents"] = None
    elif damage == "duplicate_id":
        data["incidents"].append(deepcopy(first))
    elif damage == "side":
        first["isHome"] = 0
    elif damage == "rescinded":
        first["rescinded"] = 1
    elif damage == "time":
        first["time"] = -2
    elif damage == "context":
        data["eventId"] = 999
    elif damage == "foreign_team":
        first.pop("isHome")
        first["teamId"] = 999
    elif damage == "side_conflict":
        first["teamId"] = 20
    else:
        del first["incidentType"]
    fetch.side_effect = [sofa_event(), data]
    dataset = load(cache_dir=tmp_path, on_error="collect")
    assert not dataset.complete and not dataset.match_event_records and len(dataset.match_records) == 1
    assert dataset.metadata.successful_tasks == ("match:1",) and len(dataset.errors) == 1
    assert len(list(tmp_path.rglob("*.json"))) == 1
    assert dataset.errors[0].step == "match_events" and esd.validate_dataset(dataset).valid


def test_blocked_context_skips_all_dependent_reads(fetch):
    fetch.side_effect = esd.SourceBlocked("Blocked context")
    dataset = load(tables=["match_events", "player_match_stats", "match_stats"], max_match_requests=4, on_error="collect")
    assert not dataset.complete and len(dataset.errors) == 4 and fetch.call_count == 1
    assert not dataset.metadata.successful_tasks and not dataset.match_event_records


@pytest.mark.parametrize("failed_step", ["lineups", "match_events"])
def test_independent_parts_survive_another_part_being_blocked(fetch, failed_step):
    fetch.side_effect = [sofa_event(), esd.SourceBlocked("Blocked lineups") if failed_step == "lineups" else sofa_payload(),
                         esd.SourceBlocked("Blocked incidents") if failed_step == "match_events" else incidents(),
                         {"statistics": []}]
    dataset = load(tables=["match_events", "player_match_stats", "match_stats"], max_match_requests=4, on_error="collect")
    assert not dataset.complete and len(dataset.errors) == 1 and len(dataset.match_stat_records) == 1
    assert bool(dataset.match_event_records) is (failed_step == "lineups")
    assert bool(dataset.lineup_records) is (failed_step == "match_events")
    assert esd.validate_dataset(dataset).valid


def test_valid_empty_incidents_are_distinct_from_missing_list(fetch):
    fetch.side_effect = [sofa_event(), {"incidents": []}]
    dataset = load()
    assert dataset.complete and not dataset.match_event_records and len(dataset.match_records) == 1


def test_incident_ids_and_response_positions_are_scoped_to_each_match(fetch):
    fetch.side_effect = [sofa_event(1), incidents(), sofa_event(2), incidents()]
    dataset = load(match_ids=[1, 2, 1], max_match_requests=4)
    assert dataset.complete and len(dataset.match_event_records) == 10 and fetch.call_count == 4
    assert {row.match_id for row in dataset.match_event_records} == {"1", "2"}
    assert esd.validate_dataset(dataset).valid


def test_cache_keeps_each_original_timestamp_without_readding_match(fetch, tmp_path):
    first = load(cache_dir=tmp_path)
    second = load(cache_dir=tmp_path)
    assert first.match_event_records == second.match_event_records and fetch.call_count == 2
    assert first.metadata.response_fetched_at == second.metadata.response_fetched_at
    assert second.metadata.cached_tasks == ("match:1", "match_events:1")
    data = incidents()
    data.pop("incidents")
    fetch.side_effect = [sofa_event(), data]
    assert not load(cache_dir=tmp_path, refresh=True, on_error="collect").complete
    reused = load(cache_dir=tmp_path)
    assert reused.match_event_records == first.match_event_records


def test_snapshot_and_dataframe_preserve_flags_native_json_and_nulls(fetch, tmp_path):
    pytest.importorskip("pyarrow")
    pytest.importorskip("pandas")
    dataset = load()
    restored = esd.open_dataset(dataset.save(tmp_path / "sofa"))
    assert restored == dataset and esd.validate_dataset(restored).valid
    assert str(dataset.match_events.rescinded.dtype) == "boolean"
    assert dataset.match_events.rescinded.dropna().tolist() == [False, True]
    assert dataset.match_events.rescinded.isna().sum() == 3


def test_native_sequence_does_not_collide_with_response_position_for_missing_ids(fetch):
    data = incidents()
    data["incidents"][2].pop("id")
    data["incidents"][2]["sequence"] = 3
    fetch.side_effect = [sofa_event(), data]
    rows = load().match_event_records
    assert rows[2].source_order == 2 and rows[3].source_order == 3
    assert json.loads(rows[2].source_details_json)["sequence"] == 3


def test_schema_4_snapshot_checks_original_columns_and_does_not_invent_flags(fetch, tmp_path):
    pa = pytest.importorskip("pyarrow")
    pq = pytest.importorskip("pyarrow.parquet")
    from tests.test_match_events import espn_events
    from tests.test_match_events import load as load_espn
    fetch.side_effect = None
    fetch.return_value = espn_events()
    dataset = load_espn()
    target = dataset.save(tmp_path / "v4")
    file = target / "match_events.parquet"
    with pq.ParquetFile(file) as reader:
        old = reader.read().drop_columns(["rescinded", "source_details_json"])
    pq.write_table(old, file)
    manifest = target / "manifest.json"
    raw = json.loads(manifest.read_text(encoding="utf-8"))
    raw["metadata"]["schema_version"] = "4"
    raw["tables"]["match_events"]["sha256"] = hashlib.sha256(file.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(raw), encoding="utf-8")
    before = manifest.read_bytes()
    assert esd.open_dataset(target) == dataset
    assert before == manifest.read_bytes()
    # Relabeling a schema-5 file as schema 4 cannot bypass column validation.
    pq.write_table(pa.Table.from_pylist([replace(row, rescinded=False).__dict__ for row in dataset.match_event_records]), file)
    raw["tables"]["match_events"]["sha256"] = hashlib.sha256(file.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(esd.DatasetFormatError, match="schema"):
        esd.open_dataset(target)

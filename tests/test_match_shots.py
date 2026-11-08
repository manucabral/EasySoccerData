"""Shot tables preserve source coordinates/models and bounded detail requests."""

import hashlib
import json
from copy import deepcopy
from dataclasses import replace
from unittest.mock import Mock

import pytest

import esd
from esd import _provider_datasets
from esd.exceptions import SourceError
from tests.test_match_events import espn_events
from tests.test_match_players import sofa_event, sofa_payload
from tests.test_sofascore_match_events import incidents


def shotmap():
    return {"shotmap": [
        {"id": 123, "player": {"id": 101, "name": "Player"}, "isHome": True,
         "shotType": "save", "time": 45, "addedTime": 2, "timeSeconds": 2699,
         "playerCoordinates": {"x": 88.5, "y": 31.2, "z": 0},
         "goalMouthCoordinates": {"x": 0, "y": 51.7, "z": 15.2},
         "xg": 0.0, "xgot": 0.32, "bodyPart": "right-foot", "situation": "regular"},
        {"shotType": "miss", "time": -1},
    ]}


@pytest.fixture
def fetch(monkeypatch):
    fetch = Mock()
    monkeypatch.setattr(_provider_datasets, "get_api_json", fetch)
    return fetch


def load(source="sofascore", **options):
    query = {"source": source, "league": 72 if source == "sofascore" else "test.cup", "season": 2026,
             "season_id": 228 if source == "sofascore" else None, "tables": ["shots"],
             "match_ids": [1], "max_match_requests": 2 if source == "sofascore" else 1, "request_delay": 0}
    return esd.load_dataset(**(query | options))


def test_sofascore_native_shots_retain_nulls_zero_xg_raw_coordinates_and_no_inferred_period(fetch):
    payload = shotmap()
    before = deepcopy(payload)
    fetch.side_effect = [sofa_event(), payload]
    dataset = load()
    assert dataset.complete and esd.validate_dataset(dataset).valid and fetch.call_count == 2
    assert dataset.metadata.expected_tasks == ("match:1", "shots:1")
    assert fetch.call_args.args[0].endswith("/event/1/shotmap")
    first, unknown = dataset.shot_records
    assert (first.shot_id, first.player_id, first.team_id, first.home_away) == ("123", "101", "10", "home")
    assert (first.minute, first.added_minute, first.clock_seconds) == (45, 2, 2699)
    assert (first.x, first.y, first.xg, first.xgot) == (88.5, 31.2, 0.0, 0.32)
    assert first.coordinate_system == "sofascore-native-player" and first.xg_model == "sofascore"
    assert first.source_period is None and first.is_shootout is None
    assert first.body_part == "right-foot" and first.result == "save"
    assert json.loads(first.source_details_json) == payload["shotmap"][0]
    assert unknown.shot_id is None and unknown.source_order == 1
    assert unknown.team_id is None and unknown.home_away is None and unknown.minute is None
    assert unknown.is_shootout is None and unknown.xg_model is None and unknown.coordinate_system is None
    assert json.loads(unknown.source_details_json)["time"] == -1
    assert payload == before


def test_espn_partial_attempts_share_summary_deduplicate_goals_and_separate_shootouts(fetch):
    payload = espn_events()
    play = deepcopy(payload["keyEvents"][0])
    play.update(id="shot1", type={"id": "135", "text": "Shot Blocked"}, scoringPlay=False,
                fieldPositionX=80.9, fieldPositionY=67.8, fieldPosition2X=97.2, fieldPosition2Y=52.4)
    payload["commentary"].append({"sequence": 33, "play": play})
    fetch.return_value = payload
    dataset = load("espn", tables=["shots", "match_events", "player_match_stats", "match_stats"])
    assert dataset.complete and esd.validate_dataset(dataset).valid and fetch.call_count == 1
    assert len(dataset.shot_records) == 3
    goal, penalty, shot = dataset.shot_records
    assert goal.shot_id == "g1" and goal.result == "goal" and goal.source_collection == "keyEvents"
    assert penalty.is_shootout is True and penalty.minute is None and penalty.added_minute is None
    assert shot.result == "blocked" and shot.source_type_id == "135"
    assert goal.x is None and goal.y is None and goal.coordinate_system is None
    assert (shot.x, shot.y, shot.coordinate_system) == (80.9, 67.8, "espn-native-field")
    assert json.loads(shot.source_details_json)["fieldPosition2X"] == 97.2
    assert all(row.xg is None and row.xgot is None and row.xg_model is None for row in dataset.shot_records)


@pytest.mark.parametrize("tables,cost", [(["shots"], 2), (["shots", "lineups"], 3),
                                       (["shots", "match_events"], 3), (["shots", "match_stats"], 3),
                                       (["shots", "player_match_stats", "match_events", "match_stats"], 5)])
def test_sofascore_shots_share_one_context_with_exact_preflight_budget(fetch, tables, cost):
    responses = [sofa_event()]
    if set(tables) & {"lineups", "player_match_stats"}:
        responses.append(sofa_payload())
    if "match_events" in tables:
        responses.append(incidents())
    responses.append(shotmap())
    if "match_stats" in tables:
        responses.append({"statistics": []})
    fetch.side_effect = responses
    with pytest.raises(ValueError, match="exceeding"):
        load(tables=tables, max_match_requests=cost - 1)
    fetch.assert_not_called()
    result = load(tables=tables, max_match_requests=cost)
    assert result.complete and esd.validate_dataset(result).valid and fetch.call_count == cost


@pytest.mark.parametrize("change", ["missing", "null", "duplicate", "side", "foreign_team", "context", "nan", "flag", "type"])
def test_invalid_shotmaps_fail_without_cache_publication(fetch, tmp_path, change):
    payload = shotmap()
    if change == "missing":
        payload = {}
    elif change == "null":
        payload["shotmap"] = None
    elif change == "duplicate":
        payload["shotmap"].append(deepcopy(payload["shotmap"][0]))
    elif change == "side":
        payload["shotmap"][0]["teamId"] = 20
    elif change == "foreign_team":
        payload["shotmap"][1]["teamId"] = 999
    elif change == "context":
        payload["eventId"] = 2
    elif change == "nan":
        payload["shotmap"][0]["playerCoordinates"]["x"] = float("nan")
    elif change == "flag":
        payload["shotmap"][0]["isHome"] = 0
    else:
        del payload["shotmap"][0]["shotType"]
    fetch.side_effect = [sofa_event(), payload]
    dataset = load(cache_dir=tmp_path, on_error="collect")
    assert not dataset.complete and not dataset.shot_records and dataset.match_records
    assert dataset.errors[0].step == "shots"
    fetch.reset_mock(side_effect=True)
    fetch.return_value = shotmap()
    restored = load(cache_dir=tmp_path)
    assert restored.complete and fetch.call_count == 1 and restored.metadata.cached_tasks == ("match:1",)


def test_shot_cache_retains_original_timestamps_and_reuses_response(fetch, tmp_path):
    fetch.side_effect = [sofa_event(), shotmap()]
    first = load(cache_dir=tmp_path)
    second = load(cache_dir=tmp_path)
    assert first.shot_records == second.shot_records and fetch.call_count == 2
    assert first.metadata.response_fetched_at == second.metadata.response_fetched_at
    assert second.metadata.cached_tasks == second.metadata.expected_tasks


def test_explicit_empty_shotmap_succeeds_and_context_failure_skips_dependents(fetch):
    fetch.side_effect = [sofa_event(), {"shotmap": []}]
    result = load()
    assert result.complete and not result.shot_records
    fetch.reset_mock(side_effect=True)
    fetch.side_effect = SourceError("blocked")
    failed = load(on_error="collect")
    assert fetch.call_count == 1 and not failed.complete
    assert {issue.step for issue in failed.errors} == {"match", "shots"}


def test_shot_ids_and_response_positions_are_scoped_to_each_match(fetch):
    fetch.side_effect = [sofa_event(), shotmap(), sofa_event(2), shotmap()]
    result = load(match_ids=[1, 2], max_match_requests=4)
    assert len(result.shot_records) == 4 and esd.validate_dataset(result).valid
    duplicated = replace(result, shot_records=(*result.shot_records, result.shot_records[-1]))
    assert any(issue.code == "duplicate_key" for issue in esd.validate_dataset(duplicated).errors)


def test_unsupported_source_fails_before_network_and_raw_adapter_checks_context(fetch):
    with pytest.raises(ValueError, match="Unsupported"):
        esd.load_dataset(source="scores365", league=72, season=2026, season_id=228,
                         tables=["shots"], match_ids=[1], request_delay=0)
    fetch.assert_not_called()
    with pytest.raises(ValueError):
        esd.normalize_match_shots({}, match=esd.NormalizedMatch("understat"))


@pytest.mark.parametrize("change", ["duplicate", "duplicate_commentary", "conflict", "coordinate_conflict", "own_goal", "foreign_team", "foreign_match", "null_commentary"])
def test_espn_attempts_validate_native_keys_context_and_own_goal_exclusion(fetch, change):
    payload = espn_events()
    if change == "duplicate":
        payload["keyEvents"].append(deepcopy(payload["keyEvents"][0]))
    elif change == "duplicate_commentary":
        payload["commentary"].append(deepcopy(payload["commentary"][0]))
    elif change == "conflict":
        payload["commentary"][0]["play"]["participants"][0]["athlete"]["id"] = "other"
    elif change == "coordinate_conflict":
        payload["keyEvents"][0]["fieldPositionX"] = 80.9
        payload["commentary"][0]["play"]["fieldPositionX"] = 90.1
    elif change == "own_goal":
        payload["keyEvents"][0]["type"]["id"] = "97"
        payload["commentary"][0]["play"]["type"]["id"] = "97"
    elif change == "foreign_team":
        payload["keyEvents"][0]["team"]["id"] = "foreign"
    elif change == "foreign_match":
        payload["header"]["id"] = "2"
    else:
        payload["commentary"] = None
    fetch.return_value = payload
    if change == "own_goal":
        result = load("espn")
        assert len(result.shot_records) == 1 and result.shot_records[0].is_shootout is True
    else:
        result = load("espn", on_error="collect")
        assert not result.complete and not result.shot_records and result.errors


def test_native_coordinate_values_are_not_rescaled_or_limited_to_a_guessed_pitch(fetch):
    payload = shotmap()
    payload["shotmap"][0]["playerCoordinates"] = {"x": -1.25, "y": 150.5}
    fetch.side_effect = [sofa_event(), payload]
    result = load()
    assert result.shot_records[0].x == -1.25 and result.shot_records[0].y == 150.5


def test_shot_table_remains_compatible_with_match_linkage(fetch):
    fetch.side_effect = [sofa_event(), shotmap()]
    result = load()
    assert esd.check_dataset_compatibility(result, result).can_match
    assert len(esd.link_dataset_matches(result, result).links) == 1


@pytest.mark.parametrize("version", ["1", "2", "3", "4", "5"])
def test_old_shots_migrate_without_fabricating_models_or_changing_files(tmp_path, version):
    pa = pytest.importorskip("pyarrow")
    import pyarrow.parquet as pq

    from esd._dataset_storage import _V5_SHOTS
    from tests.test_player_comparison import NOW

    shot = esd.NormalizedShot("understat", "001", "010", x=0.9, y=0.2, xg=0.0, coordinate_system="understat-native")
    data = esd.SoccerDataset(esd.DatasetMetadata("understat", "EPL", 2026, ("shots",), NOW, NOW), shot_records=(shot,))
    path = data.save(tmp_path / "old")
    file = path / "shots.parquet"
    with pq.ParquetFile(file) as reader:
        table = reader.read(columns=list(_V5_SHOTS))
    assert table.schema.field("xg").type == pa.float64()
    pq.write_table(table, file)
    manifest = json.loads((path / "manifest.json").read_text())
    manifest["metadata"]["schema_version"] = version
    manifest["tables"]["shots"]["sha256"] = hashlib.sha256(file.read_bytes()).hexdigest()
    (path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    before = {item.name: item.read_bytes() for item in path.iterdir()}
    restored = esd.open_dataset(path)
    assert restored == data and restored.metadata.schema_version == "6"
    assert restored.shot_records[0].xg_model is None and restored.shot_records[0].team_id is None
    assert before == {item.name: item.read_bytes() for item in path.iterdir()}
    assert esd.open_dataset(restored.save(tmp_path / "current")) == restored


def test_new_shots_parquet_and_nullable_dataframe_roundtrip(fetch, tmp_path):
    pytest.importorskip("pyarrow")
    pytest.importorskip("pandas")
    fetch.side_effect = [sofa_event(), shotmap()]
    dataset = load()
    assert esd.open_dataset(dataset.save(tmp_path / "shots")) == dataset
    frame = dataset.shots
    assert str(frame.shot_id.dtype) == "string" and str(frame.source_order.dtype) == "Int64"
    assert str(frame.xgot.dtype) == "Float64" and str(frame.is_shootout.dtype) == "boolean"
    assert frame.xg.iloc[0] == 0.0 and frame.xg.isna().sum() == 1

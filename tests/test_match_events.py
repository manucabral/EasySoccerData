"""Events retain native keys, nullable participants and separate shootout clocks."""

import json
from copy import deepcopy
from dataclasses import replace
from unittest.mock import Mock

import pytest

import esd
from esd import _provider_datasets
from tests.test_match_players import espn_payload, scores_payload


def espn_events(identifier="1"):
    data = espn_payload(identifier)
    data["keyEvents"] = [
        {"id": "g1", "type": {"id": "70", "text": "Goal"}, "period": {"number": 1},
         "clock": {"value": 2690, "displayValue": "45'+2'"}, "shootout": False, "scoringPlay": True,
         "team": {"id": "10"}, "participants": [{"athlete": {"id": "101", "displayName": "Player"}}]},
        {"id": "s1", "type": {"id": "76"}, "period": {"number": 2}, "clock": {"displayValue": "67'"},
         "team": {"id": "10"}, "participants": [{"athlete": {"id": "102"}}, {"athlete": {"id": "101"}}]},
    ]
    data["commentary"] = [
        {"sequence": 7, "play": deepcopy(data["keyEvents"][0])},
        {"sequence": 99, "play": {"id": "p1", "type": {"id": "104"}, "period": {"number": 5},
                                  "clock": {"value": 7200, "displayValue": "120'"},
                                  "team": {"displayName": "Native team"},
                                  "participants": [{"athlete": {"displayName": "Native player"}}]}},
    ]
    return data


def scores_events(identifier=1):
    data = scores_payload(identifier)
    data["game"]["events"] = [
        {"order": 1, "stageId": 9, "statusId": 8, "gameTime": 90.0, "addedTime": 5,
         "gameTimeDisplay": "90'", "competitorId": 10, "playerId": 101,
         "eventType": {"id": 1, "name": "Localized goal", "subTypeId": 3}},
        {"order": 2, "stageId": 11, "gameTime": 121.0, "gameTimeDisplay": "1", "competitorId": 20,
         "eventType": {"id": 6, "name": "Localized miss", "subTypeId": -1}},
        {"order": 3, "eventType": {"id": 1000}, "competitorId": 10, "playerId": 102, "extraPlayers": [101]},
    ]
    return data


@pytest.fixture
def fetch(monkeypatch):
    fetch = Mock()
    monkeypatch.setattr(_provider_datasets, "get_api_json", fetch)
    return fetch


def load(source="espn", **options):
    query = {"source": source, "league": "test.cup" if source == "espn" else "72", "season": 2026,
             "season_id": None if source == "espn" else 228, "tables": ["match_events"],
             "match_ids": [1], "max_match_requests": 1, "request_delay": 0}
    return esd.load_dataset(**(query | options))


@pytest.mark.parametrize("source,payload", [("espn", espn_events), ("scores365", scores_events)])
def test_bounded_event_downloads_and_nullable_native_fields(fetch, source, payload):
    data = payload()
    original = deepcopy(data)
    fetch.return_value = data
    dataset = load(source)
    assert dataset.complete and esd.validate_dataset(dataset).valid and fetch.call_count == 1
    assert set(dataset.metadata.tables) == {"match_events", "matches", "teams"}
    assert not dataset.lineup_records and not dataset.player_match_stat_records
    assert data == original and len(dataset.match_event_records) == 3
    first, penalty, substitution = (dataset.match_event_records[i] for i in ((0, 2, 1) if source == "espn" else (0, 1, 2)))
    assert first.added_minute == (2 if source == "espn" else 5)
    assert penalty.is_shootout is True and penalty.minute is None and penalty.added_minute is None
    assert penalty.player_id is None
    assert substitution.player_role == "incoming" and substitution.related_player_role == "outgoing"
    assert substitution.related_player_id == "101" and substitution.player_id == "102"
    assert esd.normalize_match_events(data, match=dataset.match_records[0]) == dataset.match_event_records
    if source == "espn":
        assert first.clock_seconds == 2690 and first.minute == 45
        assert first.event_id == "g1" and first.source_order is None
        assert penalty.source_collection == "commentary.play" and penalty.source_order == 99
        assert penalty.player_name == "Native player" and penalty.team_id is None
    else:
        assert first.source_athlete_id == "777" and first.event_id is None and first.source_order == 1
        assert first.event_type == "penalty_scored" and penalty.event_type == "penalty_missed"
        assert penalty.source_game_time == 121 and penalty.source_clock == "1"
        assert substitution.minute is None and substitution.is_shootout is None
        assert "timezoneName=UTC" in fetch.call_args.args[0]


@pytest.mark.parametrize("source,payload,cost", [("espn", espn_events, 1), ("scores365", scores_events, 2)])
def test_combined_events_players_and_totals_share_responses(fetch, source, payload, cost):
    data = payload()
    fetch.side_effect = [data] if source == "espn" else [data, {"games": [data["game"]], "statistics": []}]
    dataset = load(source, tables=["match_events", "player_match_stats", "match_stats"], max_match_requests=cost)
    assert dataset.complete and esd.validate_dataset(dataset).valid and fetch.call_count == cost
    assert len(dataset.lineup_records) == (3 if source == "espn" else 2) and dataset.player_match_stat_records
    assert len(dataset.match_stat_records) == 1 and len(dataset.match_event_records) == 3


@pytest.mark.parametrize("source,payload", [("espn", espn_events), ("scores365", scores_events)])
def test_events_only_ignores_unselected_player_statistics(fetch, source, payload):
    data = payload()
    if source == "espn":
        data["rosters"] = "unselected malformed rosters"
        data["boxscore"] = None
    else:
        data["game"]["homeCompetitor"]["lineups"] = "unselected malformed lineups"
    fetch.return_value = data
    assert load(source).complete


@pytest.mark.parametrize("source,payload", [("espn", espn_events), ("scores365", scores_events)])
@pytest.mark.parametrize("damage", ["missing_list", "bad_list", "duplicate", "team", "clock", "match", "type"])
def test_bad_events_fail_before_cache_publication_and_keep_partial_coverage(fetch, tmp_path, source, payload, damage):
    data = payload()
    group, key = (data, "keyEvents") if source == "espn" else (data["game"], "events")
    if damage == "missing_list":
        del group[key]
    elif damage == "bad_list":
        group[key] = None
    elif damage == "duplicate":
        group[key].append(deepcopy(group[key][0]))
    elif damage == "team":
        if source == "espn":
            group[key][0]["team"] = {"id": "999"}
        else:
            group[key][0]["competitorId"] = 999
    elif damage == "clock":
        if source == "espn":
            group[key][0]["clock"]["value"] = -1
        else:
            group[key][0]["addedTime"] = -1
    elif damage == "type":
        group[key][0]["type" if source == "espn" else "eventType"] = None
    elif source == "espn":
        data["header"]["id"] = "2"
    else:
        group["seasonNum"] = 999
    fetch.return_value = data
    dataset = load(source, cache_dir=tmp_path, on_error="collect")
    assert not dataset.complete and len(dataset.errors) == 1 and not dataset.match_event_records
    assert not list(tmp_path.rglob("*.json")) and not dataset.metadata.response_fetched_at
    assert esd.validate_dataset(dataset).valid


@pytest.mark.parametrize("source,payload", [("espn", espn_events), ("scores365", scores_events)])
def test_explicit_empty_event_list_is_valid_and_not_missing(fetch, source, payload):
    data = payload()
    if source == "espn":
        data["keyEvents"], data["commentary"] = [], []
    else:
        data["game"]["events"] = []
    fetch.return_value = data
    dataset = load(source)
    assert dataset.complete and not dataset.match_event_records


def test_commentary_duplicate_prefers_native_key_event_but_rejects_conflicting_identity(fetch):
    data = espn_events()
    data["commentary"][0]["play"]["team"] = {"displayName": "No native team ID"}
    fetch.return_value = data
    assert load().match_event_records[0].team_id == "10"
    data["commentary"][0]["play"]["team"]["id"] = "20"
    with pytest.raises(esd.DatasetLoadError):
        load()


def test_365_anonymous_member_and_shootout_without_player_remain_unknown(fetch):
    data = scores_events()
    data["game"]["members"].append({"competitorId": 10})
    fetch.return_value = data
    assert load("scores365").match_event_records[1].player_id is None


def test_failed_refresh_does_not_replace_valid_event_cache(fetch, tmp_path):
    fetch.return_value = espn_events()
    first = load(cache_dir=tmp_path)
    fetch.return_value = {"header": {}}
    assert not load(cache_dir=tmp_path, refresh=True, on_error="collect").complete
    restored = load(cache_dir=tmp_path)
    assert first.match_event_records == restored.match_event_records
    assert first.metadata.response_fetched_at == restored.metadata.response_fetched_at
    assert fetch.call_count == 2 and restored.metadata.cached_tasks == ("match_details:1",)


def test_invalid_365_events_keep_separate_valid_team_statistics(fetch):
    data = scores_events()
    broken = deepcopy(data)
    del broken["game"]["events"]
    fetch.side_effect = [broken, {"games": [data["game"]], "statistics": []}]
    dataset = load("scores365", tables=["match_events", "match_stats"], max_match_requests=2, on_error="collect")
    assert not dataset.complete and not dataset.match_event_records
    assert len(dataset.match_stat_records) == 1 and len(dataset.match_records) == 1
    assert dataset.metadata.successful_tasks == ("match_stats:1",)
    assert len(dataset.errors) == 1 and esd.validate_dataset(dataset).valid


def test_partial_download_preserves_successful_match_events(fetch):
    fetch.side_effect = [espn_events("1"), esd.SourceBlocked("Blocked fixture")]
    dataset = load(match_ids=[1, 2], max_match_requests=2, on_error="collect")
    assert not dataset.complete and len(dataset.match_event_records) == 3 and len(dataset.errors) == 1
    assert dataset.metadata.successful_tasks == ("match_details:1",)


def test_own_goal_event_team_is_not_replaced_with_player_roster_team(fetch):
    data = espn_events()
    data["keyEvents"][0]["type"] = {"id": "97"}
    data["keyEvents"][0]["team"]["id"] = "20"
    data["commentary"] = []
    fetch.return_value = data
    dataset = load(tables=["match_events", "lineups"])
    assert dataset.match_event_records[0].team_id == "20"
    assert esd.validate_dataset(dataset).valid


def test_espanol_red_card_text_does_not_infer_second_yellow_or_participant_roles(fetch):
    data = espn_events()
    data["keyEvents"][0].update(type={"id": "93"}, text="Second yellow card in source text")
    data["commentary"] = []
    fetch.return_value = data
    row = load().match_event_records[0]
    assert row.event_type == "red_card" and row.player_role is None


@pytest.mark.parametrize("source,payload", [("espn", espn_events), ("scores365", scores_events)])
def test_response_cache_reuse_and_event_keys_are_scoped_to_each_match(fetch, tmp_path, source, payload):
    fetch.side_effect = [payload(1), payload(2)] if source == "scores365" else [payload("1"), payload("2")]
    options = {"match_ids": [1, 2, 1], "max_match_requests": 2, "cache_dir": tmp_path}
    first = load(source, **options)
    second = load(source, **options)
    assert len(first.match_event_records) == 6 and first.complete and second.complete
    assert first.match_event_records == second.match_event_records
    assert first.metadata.response_fetched_at == second.metadata.response_fetched_at
    assert len(second.metadata.cached_tasks) == 2 and fetch.call_count == 2


@pytest.mark.parametrize("source", ["sofascore", "fbref", "understat", "goaloo", "promiedos", "besoccer", "transfermarkt"])
def test_unsupported_provider_contract_fails_before_http(fetch, source):
    assert "match_events" not in esd.get_dataset_capabilities(source).tables
    with pytest.raises(ValueError):
        load(source)
    fetch.assert_not_called()


@pytest.mark.parametrize("options", [{"match_ids": []}, {"match_ids": [1, 2]}, {"start_date": "2026-11-03"},
                                    {"tables": ["match_events", "standings"]}, {"match_ids": [True]}])
def test_bad_scope_and_request_budgets_fail_before_http(fetch, options):
    with pytest.raises(ValueError):
        load(**options)
    fetch.assert_not_called()


@pytest.mark.parametrize("version", ["1", "2", "3"])
def test_legacy_snapshots_do_not_claim_or_fabricate_event_table(fetch, tmp_path, version):
    pytest.importorskip("pyarrow")
    fetch.return_value = espn_events()
    full = load()
    dataset = replace(full, metadata=replace(full.metadata, tables=("matches", "teams")), match_event_records=())
    path = dataset.save(tmp_path / "old")
    manifest = path / "manifest.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["metadata"]["schema_version"] = version
    manifest.write_text(json.dumps(data), encoding="utf-8")
    before = manifest.read_bytes()
    restored = esd.open_dataset(path)
    assert restored == dataset and restored.metadata.schema_version == "4"
    assert "match_events" not in restored.metadata.tables and not restored.match_event_records
    assert manifest.read_bytes() == before
    new = load().save(tmp_path / "events")
    file = new / "manifest.json"
    raw = json.loads(file.read_text(encoding="utf-8"))
    raw["metadata"]["schema_version"] = version
    file.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(esd.DatasetFormatError, match="require schema version 4"):
        esd.open_dataset(new)


def test_nullable_frames_and_event_snapshots_roundtrip(fetch, tmp_path):
    pytest.importorskip("pandas")
    pytest.importorskip("pyarrow")
    fetch.return_value = espn_events()
    dataset = load()
    assert esd.open_dataset(dataset.save(tmp_path / "events")) == dataset
    frame = dataset.match_events
    assert str(frame.minute.dtype) == str(frame.source_order.dtype) == "Int64"
    assert str(frame.clock_seconds.dtype) == "Float64" and str(frame.is_shootout.dtype) == "boolean"
    assert frame.player_id.isna().sum() == 1
    assert esd.normalized_to_dataframe([], table="match_events").dtypes.equals(frame.dtypes)


@pytest.mark.parametrize("change,code", [({"minute": -1}, "invalid_event_clock"),
                                         ({"is_shootout": True, "minute": 120}, "shootout_match_minute"),
                                         ({"event_id": None, "source_order": None}, "missing_event_key"),
                                         ({"event_type": "invented"}, "invalid_event_type"),
                                         ({"team_id": "999"}, "event_team_mismatch"),
                                         ({"match_id": "999"}, "unrequested_match"),
                                         ({"player_role": "scorer"}, "invalid_event_role")])
def test_validation_detects_event_identity_scope_and_clocks(fetch, change, code):
    fetch.return_value = espn_events()
    dataset = load()
    dataset = replace(dataset, match_event_records=(replace(dataset.match_event_records[0], **change),))
    assert code in {issue.code for issue in esd.validate_dataset(dataset).errors}


@pytest.mark.parametrize("native,subtype,expected", [(1, 1, "goal"), (1, 2, "own_goal"), (1, 3, "penalty_scored"),
                                                    (2, -1, "yellow_card"), (3, -1, "red_card"),
                                                    (6, -1, "penalty_missed"), (9911, 9, "other")])
def test_365_native_type_keys_do_not_depend_on_localized_labels(fetch, native, subtype, expected):
    data = scores_events()
    data["game"]["events"][0]["eventType"] = {"id": native, "subTypeId": subtype, "name": "Unrelated localized name"}
    fetch.return_value = data
    assert load("scores365").match_event_records[0].event_type == expected

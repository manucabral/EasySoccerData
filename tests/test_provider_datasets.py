"""Dataset source contracts verified without HTTP or browser access."""

from copy import deepcopy

import pytest

import esd
from esd import _provider_datasets as providers
from esd.exceptions import SourceBlocked, SourceError


def sofa_event(match_id=1, **changes):
    data = {
        "id": match_id, "season": {"id": 61627},
        "tournament": {"id": 1, "name": "Premier League", "uniqueTournament": {"id": 17}},
        "homeTeam": {"id": 10, "name": "Home"}, "awayTeam": {"id": 20, "name": "Away"},
        "startTimestamp": 1723834800, "status": {"type": "finished"},
        "homeScore": {"current": 2}, "awayScore": {"current": 0},
    }
    data.update(changes)
    return data


def game(match_id=1, competition=72, **changes):
    data = {"id": match_id, "competitionId": competition, "seasonNum": 228,
            "startTime": "2024-08-16T19:00:00Z", "statusGroup": 4,
            "homeCompetitor": {"id": 10, "name": "Home", "score": 2},
            "awayCompetitor": {"id": 20, "name": "Away", "score": 0}}
    data.update(changes)
    return data


def understat_match(match_id="26602", result=True):
    return {"id": match_id, "isResult": result, "datetime": "2024-08-16 19:00:00",
            "h": {"id": "89", "title": "Home"}, "a": {"id": "228", "title": "Away"},
            "goals": {"h": "1", "a": "0"}, "xG": {"h": "2.43", "a": "0.41"},
            "forecast": {"w": "0.86", "d": "0.10", "l": "0.04"}}


def load(source, **kwargs):
    defaults = {
        "sofascore": {"league": 17, "season_id": 61627},
        "scores365": {"league": 72, "start_date": "2024-08-16", "end_date": "2024-08-16"},
        "understat": {"league": "EPL", "source_timezone": "UTC"},
    }[source]
    return esd.load_dataset(source=source, season=2024, request_delay=0, **(defaults | kwargs))


def test_capabilities_are_explicit_and_not_mutable():
    matrix = esd.get_dataset_capabilities()
    assert len(matrix) == 9
    assert all(contract.tables for contract in matrix.values())
    assert "shots" in matrix["understat"].tables
    matrix.clear()
    assert len(esd.get_dataset_capabilities()) == 9
    with pytest.raises(ValueError):
        esd.get_dataset_capabilities("unknown")


@pytest.mark.parametrize("source,options", [
    ("sofascore", {"season_id": None}), ("sofascore", {"tables": ["shots"]}),
    ("scores365", {"start_date": None}), ("scores365", {"end_date": "2024-08-15"}),
    ("scores365", {"tables": ["standings"]}), ("understat", {"season_id": 2024}),
    ("understat", {"match_ids": [26602]}), ("sofascore", {"max_pages": 0}),
])
def test_invalid_selection_never_calls_source(monkeypatch, source, options):
    monkeypatch.setattr(providers, "get_api_json", lambda *a, **k: pytest.fail("Unexpected request"))
    with pytest.raises(ValueError):
        load(source, **options)


def test_scores_filters_ignored_competition_filter_and_cache_resume(monkeypatch, tmp_path):
    payload = {"games": [game(), game(2, competition=7)]}
    calls = []
    monkeypatch.setattr(providers, "get_api_json", lambda url, **k: calls.append(url) or deepcopy(payload))
    result = load("scores365", season_id=228, cache_dir=tmp_path)
    assert result.complete
    assert [row.match_id for row in result.match_records] == ["1"]
    assert result.match_records[0].source_season_id == "228"
    assert result.metadata.coverage_scope == "date_range"
    assert len(result.team_records) == 2
    progress = []
    resumed = load("scores365", season_id=228, cache_dir=tmp_path, progress=progress.append)
    assert resumed.complete and len(calls) == 1
    assert progress[0].cached
    assert resumed.metadata.response_fetched_at == result.metadata.response_fetched_at


@pytest.mark.parametrize("payload", [
    {}, {"games": [game(startTime="2024-08-17T19:00:00Z")]},
    {"games": [game(seasonNum=229)]},
])
def test_scores_rejects_missing_out_of_window_or_other_season(monkeypatch, payload):
    monkeypatch.setattr(providers, "get_api_json", lambda *a, **k: payload)
    result = load("scores365", season_id=228, on_error="collect")
    assert not result.complete and len(result.errors) == 1
    assert not result.match_records


def test_scores_service_also_applies_competition_filter(monkeypatch):
    from esd.scores365.service import Scores365Service

    service = Scores365Service()
    monkeypatch.setattr(service, "_fetch", lambda url: {"games": [game(), game(2, 7)]})
    assert [row.id for row in service.get_games(competition_id=72)] == [1]
    assert len(service.get_games()) == 2


def test_scores_standings_require_matching_native_season(monkeypatch):
    payload = {"standings": [{"competitionId": 72, "seasonNum": 228,
                              "displayName": "Total", "rows": [
                                  {"competitor": {"id": 10, "name": "Home"}, "points": 3}]}]}
    monkeypatch.setattr(providers, "get_api_json", lambda *a, **k: payload)
    result = load("scores365", season_id=228, tables=["standings"])
    assert result.complete and result.standing_records[0].source_season_id == "228"
    partial = load("scores365", season_id=229, tables=["standings"], on_error="collect")
    assert not partial.complete and not partial.standing_records


def test_scores_partial_range_round_trip(monkeypatch, tmp_path):
    def fetch(url, **kwargs):
        if "17/08/2024" in url:
            raise SourceError("Unavailable day")
        return {"games": [game()]}

    monkeypatch.setattr(providers, "get_api_json", fetch)
    result = load("scores365", end_date="2024-08-17", on_error="collect")
    assert not result.complete and len(result.match_records) == 1
    assert result.metadata.successful_tasks == ("matches:2024-08-16",)
    assert len(result.metadata.expected_tasks) == 2
    pytest.importorskip("pyarrow")
    result.save(tmp_path / "partial")
    assert esd.open_dataset(tmp_path / "partial") == result


def test_sofa_paginates_both_directions_deduplicates_and_preserves_ids(monkeypatch):
    pages = {
        "last/0": {"events": [sofa_event()], "hasNextPage": True},
        "last/1": {"events": [sofa_event(2)], "hasNextPage": False},
        "next/0": {"events": [sofa_event(3, status={"type": "notstarted"})], "hasNextPage": False},
    }
    monkeypatch.setattr(providers, "get_api_json", lambda url, **k: deepcopy(pages[url.rsplit("/events/", 1)[1]]))
    result = load("sofascore")
    assert result.complete and len(result.match_records) == 3
    assert result.match_records[0].competition_id == "17"
    assert result.match_records[0].source_season_id == "61627"
    assert result.match_records[-1].home_score is None
    assert set(result.metadata.expected_tasks) == {"matches:last/0", "matches:last/1", "matches:next/0"}


@pytest.mark.parametrize("payload,limit", [
    ({"events": []}, 100),
    ({"events": [], "hasNextPage": True}, 100),
    ({"events": [sofa_event()], "hasNextPage": True}, 100),
    ({"events": [sofa_event()], "hasNextPage": True}, 1),
    ({"events": [sofa_event(season={"id": 1})], "hasNextPage": False}, 100),
    ({"events": [sofa_event(tournament={"uniqueTournament": {"id": 1}})], "hasNextPage": False}, 100),
])
def test_sofa_pagination_and_identity_failures_are_partial(monkeypatch, payload, limit):
    calls = []
    monkeypatch.setattr(providers, "get_api_json", lambda url, **k: calls.append(url) or deepcopy(payload))
    result = load("sofascore", max_pages=limit, on_error="collect")
    assert not result.complete and result.errors
    assert len(calls) <= 4


def test_sofa_block_is_explicit_partial_error(monkeypatch):
    def blocked(*a, **k):
        raise SourceBlocked("HTTP 403")

    monkeypatch.setattr(providers, "get_api_json", blocked)
    with pytest.raises(esd.DatasetLoadError) as caught:
        load("sofascore")
    assert caught.value.dataset.errors[0].error_type == "SourceBlocked"
    assert not caught.value.dataset.complete


def test_sofa_standings_keep_native_context(monkeypatch):
    payload = {"standings": [{"id": 9, "name": "Total", "rows": [
        {"team": {"id": 10, "name": "Home"}, "position": 1, "points": 3,
         "scoreDiffFormatted": "+2"}]}]}
    monkeypatch.setattr(providers, "get_api_json", lambda *a, **k: payload)
    result = load("sofascore", tables=["standings"])
    assert result.complete
    row = result.standing_records[0]
    assert (row.competition_id, row.source_season_id, row.table_id, row.goal_difference) == ("17", "61627", "9", 2)


@pytest.fixture
def understat_payload():
    return {"datesData": [understat_match(), understat_match("26603", False)],
            "playersData": [{"id": "9", "player_name": "Player", "team_title": "Home,Away",
                             "games": "10", "xG": "2.43", "xA": "1.25"}]}


def test_understat_tables_shot_selection_cache_and_parquet(monkeypatch, tmp_path, understat_payload):
    calls = []

    def fetch(url, **kwargs):
        calls.append(url)
        if "/getMatchData/" in url:
            return {"shotsData": {"h": [{"id": "584101", "match_id": "26602", "player_id": "9",
                                        "X": "0.912", "Y": "0.485", "xG": "0.341"}], "a": []}}
        return deepcopy(understat_payload)

    monkeypatch.setattr(providers, "get_api_json", fetch)
    options = {"tables": ["matches", "match_stats", "player_stats", "shots"], "match_ids": [26602],
                   "cache_dir": tmp_path / "cache"}
    result = load("understat", **options)
    assert result.complete and len(calls) == 2
    assert result.match_records[0].kickoff.utcoffset().total_seconds() == 0
    assert result.match_records[1].home_score is None
    assert result.match_stat_records[0].home_xg == 2.43
    assert result.player_stat_records[0].source_team_names == "Home,Away"
    assert result.shot_records[0].coordinate_system == "understat-native"
    assert result.shot_records[0].x == 0.912
    assert result.metadata.requested_match_ids == ("26602",)
    resumed = load("understat", **options)
    assert len(calls) == 2 and len(resumed.metadata.cached_tasks) == 3
    pytest.importorskip("pandas")
    assert str(result.shots.xg.dtype) == "Float64"
    assert str(result.player_stats.games.dtype) == "Int64"
    assert result.matches.merge(result.match_stats, on=["source", "match_id"]).shape[0] == 2
    pytest.importorskip("pyarrow")
    result.save(tmp_path / "snapshot")
    assert esd.open_dataset(tmp_path / "snapshot") == result


def test_understat_shots_are_opt_in(monkeypatch, understat_payload):
    calls = []
    monkeypatch.setattr(providers, "get_api_json", lambda url, **k: calls.append(url) or understat_payload)
    result = load("understat")
    assert result.complete and len(calls) == 1 and not result.shot_records


@pytest.mark.parametrize("options", [
    {"source_timezone": None}, {"tables": ["shots"], "match_ids": [999]},
    {"tables": ["shots"], "match_ids": [26603]},
])
def test_understat_ambiguous_time_and_wrong_shot_scope_fail(monkeypatch, understat_payload, options):
    monkeypatch.setattr(providers, "get_api_json", lambda *a, **k: understat_payload)
    result = load("understat", on_error="collect", **options)
    assert not result.complete and not result.match_records


def test_understat_html_fallback_uses_public_page_and_preserves_errors(monkeypatch):
    pages = []

    def no_json(*a, **k):
        raise SourceError("Not JSON")

    monkeypatch.setattr(providers, "get_api_json", no_json)
    monkeypatch.setattr(providers, "get_text", lambda url, **k: pages.append(url) or "<html>Maintenance</html>")
    result = load("understat", on_error="collect")
    assert pages == ["https://understat.com/league/EPL/2024"]
    assert not result.complete and "maintenance" in result.errors[0].message


@pytest.mark.parametrize("shots", [{}, {"h": []}, {"h": [], "a": None},
                                    [{"id": "9", "match_id": "999"}]])
def test_understat_missing_shot_sides_or_wrong_match_are_errors(monkeypatch, shots):
    def fetch(url, **kwargs):
        return {"shots": shots} if "/getMatchData/" in url else {"dates": [understat_match()]}

    monkeypatch.setattr(providers, "get_api_json", fetch)
    result = load("understat", tables=["shots"], on_error="collect")
    assert not result.complete and not result.shot_records


def test_understat_valid_embedded_fallback(monkeypatch):
    def no_json(*a, **k):
        raise SourceError("Not JSON")

    monkeypatch.setattr(providers, "get_api_json", no_json)
    html = r"<script>var datesData = JSON.parse('\x5B\x5D');</script>"
    monkeypatch.setattr(providers, "get_text", lambda *a, **k: html)
    assert load("understat").complete


@pytest.mark.parametrize("table,model", [
    ("shots", esd.NormalizedShot), ("match_stats", esd.NormalizedMatchStats),
    ("player_stats", esd.NormalizedPlayerStats),
])
def test_new_tables_have_the_same_empty_and_populated_types(table, model):
    pytest.importorskip("pandas")
    empty = esd.normalized_to_dataframe([], table=table)
    populated = esd.normalized_to_dataframe([model(source="understat")], table=table)
    assert empty.dtypes.equals(populated.dtypes)


def test_progress_exceptions_propagate_unchanged(monkeypatch):
    monkeypatch.setattr(providers, "get_api_json", lambda *a, **k: {"games": []})

    def callback(progress):
        raise RuntimeError("Callback failed")

    with pytest.raises(RuntimeError, match="Callback failed"):
        load("scores365", progress=callback, on_error="collect")

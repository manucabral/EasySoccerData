"""Provider selection, normalized compatibility, cache and storage regressions."""

from copy import deepcopy

import pytest

import esd
from esd import _provider_datasets as providers
from esd import _remaining_datasets as remaining
from esd.exceptions import SourceError

FBREF_HTML = """
<html><body><table id="sched_2024_9"><caption><a href="/en/comps/9/">League</a></caption><tbody>
<tr><td data-stat="home_team"><a href="/en/squads/aaa/">Home</a></td>
<td data-stat="away_team"><a href="/en/squads/bbb/">Away</a></td>
<td data-stat="start_time">19:00</td><td data-stat="score">0–1</td>
<td data-stat="home_xg">0.5</td><td data-stat="away_xg">1.2</td>
<td data-stat="match_report"><a href="/en/matches/m1/Report">Report</a></td></tr>
</tbody></table></body></html>
"""
BE_HTML = """
<html><head><link rel="canonical" href="https://es.besoccer.com/livescore/2024-08-16"></head><body>
<div class="panel"><a data-cy="competitionName" href="/competicion/premier_league">League</a>
<a id="match-123" data-local-id="10" data-visitor-id="20" starttime="2024-08-16T19:00:00+01:00" data-status-id="4">
<div class="team-info"><div class="team-name">Home</div></div>
<div class="team-info"><div class="team-name">Away</div></div>
<span class="r1">0</span><span class="r2">1</span></a></div></body></html>
"""


def load(source, **kwargs):
    defaults = {
        "goaloo": {"league": 36, "source_season": "2024-2025", "source_timezone": "UTC"},
        "fbref": {
            "league": 9,
            "source_timezone": "UTC",
            "start_date": "2024-08-16",
            "end_date": "2024-08-16",
        },
        "promiedos": {
            "league": "hc",
            "source_timezone": "UTC",
            "start_date": "2024-08-16",
            "end_date": "2024-08-16",
        },
        "besoccer": {
            "league": "premier_league",
            "start_date": "2024-08-16",
            "end_date": "2024-08-16",
        },
        "transfermarkt": {"league": "GB1", "tables": ["teams"], "club_ids": [281]},
    }[source]
    return esd.load_dataset(source=source, season=2024, request_delay=0, **(defaults | kwargs))


@pytest.fixture
def goaloo():
    return {
        "LeagueInfo": [36, "League", "2024-2025"],
        "TeamInfo": [[10, "Home"], [20, "Away"]],
        "ScheduleList": {"R_1": [[1, 36, -1, "2024-08-16 19:00", 10, 20, "0-1", "0-0"]]},
        "TotalScore": [[0, 1, 10, 0, 1, 0, 0, 1, 0, 1, -1, 0, 0, 0, 0, 0, 0]],
    }


@pytest.fixture
def promiedos():
    return {
        "leagues": [
            {
                "id": "hc",
                "name": "League",
                "games": [
                    {
                        "id": "p1",
                        "teams": [{"id": "10", "name": "Home"}, {"id": "20", "name": "Away"}],
                        "start_time": "16-08-2024 19:00",
                        "status": {"enum": 3},
                        "scores": [0, 1],
                    }
                ],
            }
        ]
    }


def test_goaloo_season_teams_and_standings_roundtrip(monkeypatch, goaloo, tmp_path):
    monkeypatch.setattr(providers, "get_api_json", lambda *a, **k: deepcopy(goaloo))
    result = load("goaloo", tables=["matches", "standings"], cache_dir=tmp_path / "cache")
    assert result.complete
    assert len(result.team_records) == 2 and result.standing_records[0].points == 0
    assert result.match_records[0].source_status == "-1"
    assert result.match_records[0].source_season_id == "2024-2025"
    monkeypatch.setattr(providers, "get_api_json", lambda *a, **k: pytest.fail("Unexpected HTTP"))
    resumed = load("goaloo", tables=["matches", "standings"], cache_dir=tmp_path / "cache")
    assert resumed.complete and resumed.metadata.cached_tasks
    pytest.importorskip("pyarrow")
    result.save(tmp_path / "snapshot")
    assert esd.open_dataset(tmp_path / "snapshot") == result


def test_goaloo_teams_only_and_unknown_score(monkeypatch, goaloo):
    monkeypatch.setattr(providers, "get_api_json", lambda *a, **k: goaloo)
    assert load("goaloo", tables=["teams"]).complete
    goaloo["ScheduleList"]["R_1"][0][6] = ""
    result = load("goaloo")
    assert result.match_records[0].home_score is None


@pytest.mark.parametrize("change", ["season", "competition", "schedule", "row", "timezone"])
def test_goaloo_rejects_incompatible_source_data(monkeypatch, goaloo, change):
    options = {}
    if change == "season":
        goaloo["LeagueInfo"][2] = "2025-2026"
    elif change == "competition":
        goaloo["LeagueInfo"][0] = 1
    elif change == "schedule":
        goaloo.pop("ScheduleList")
    elif change == "row":
        goaloo["ScheduleList"]["R_1"][0][1] = 1
    else:
        options["source_timezone"] = None
    monkeypatch.setattr(providers, "get_api_json", lambda *a, **k: goaloo)
    result = load("goaloo", on_error="collect", **options)
    assert not result.complete and not result.match_records


def test_fbref_native_ids_utc_xg_and_cache(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(remaining, "get_text", lambda url, **k: calls.append(url) or FBREF_HTML)
    result = load("fbref", tables=["matches", "match_stats"], cache_dir=tmp_path)
    assert result.complete and result.match_records[0].match_id == "m1"
    assert result.match_records[0].home_team_id == "aaa"
    assert result.match_records[0].home_score == 0
    assert result.match_records[0].kickoff.hour == 19
    assert result.match_stat_records[0].away_xg == 1.2
    assert result.metadata.coverage_scope == "date_range"
    assert load("fbref", tables=["matches", "match_stats"], cache_dir=tmp_path).complete
    assert len(calls) == 1


@pytest.mark.parametrize(
    "text",
    [
        "<html>Maintenance</html>",
        FBREF_HTML.replace("/en/matches/m1/Report", ""),
        FBREF_HTML.replace("/en/comps/9/", ""),
        "<title>Just a moment</title>",
    ],
)
def test_fbref_missing_shape_identity_or_block_is_error(monkeypatch, text):
    monkeypatch.setattr(remaining, "get_text", lambda *a, **k: text)
    result = load("fbref", on_error="collect")
    assert not result.complete and not result.match_records


def test_fbref_comment_table_and_unplayed_scores(monkeypatch):
    text = "<html><body><!--" + FBREF_HTML + "--></body></html>"
    text = text.replace("0–1", "")
    monkeypatch.setattr(remaining, "get_text", lambda *a, **k: text)
    result = load("fbref")
    assert result.complete and result.match_records[0].home_score is None


def test_fbref_penalty_scores_do_not_replace_match_scores(monkeypatch):
    monkeypatch.setattr(
        remaining, "get_text", lambda *a, **k: FBREF_HTML.replace("0–1", "1 (4)–1 (3)")
    )
    row = load("fbref").match_records[0]
    assert row.home_score == row.away_score == 1


def test_fbref_stats_only_retains_date_range_scope(monkeypatch):
    monkeypatch.setattr(remaining, "get_text", lambda *a, **k: FBREF_HTML)
    result = load("fbref", tables=["match_stats"])
    assert result.complete and result.metadata.coverage_scope == "date_range"
    assert not result.match_records and result.match_stat_records[0].home_xg == 0.5


def test_fbref_rate_limit_paces_fetches_not_cache(monkeypatch):
    from esd import _response_reader

    sleeps = []
    monkeypatch.setattr(_response_reader.time, "monotonic", lambda: 0)
    monkeypatch.setattr(_response_reader.time, "sleep", sleeps.append)
    monkeypatch.setattr(remaining, "get_text", lambda *a, **k: FBREF_HTML)
    result = load("fbref", end_date="2024-08-17")
    assert result.complete and sleeps == [60 / 9]


def test_promiedos_preserves_raw_dates_and_filters_leagues(monkeypatch, promiedos):
    promiedos["leagues"].append({"id": "other", "games": [{"id": "bad"}]})
    captured = []
    monkeypatch.setattr(
        remaining, "get_api_json", lambda url, **k: captured.append(k) or deepcopy(promiedos)
    )
    result = load("promiedos")
    assert result.complete and len(result.match_records) == 1
    assert result.match_records[0].kickoff.isoformat() == "2024-08-16T19:00:00+00:00"
    assert result.match_records[0].competition_id == "hc"
    assert captured[0]["headers"]["X-VER"]
    assert promiedos["leagues"][0]["games"][0]["start_time"] == "16-08-2024 19:00"


@pytest.mark.parametrize("payload", [{}, {"leagues": [{"id": "hc"}]}])
def test_promiedos_missing_data_is_not_empty_success(monkeypatch, payload):
    monkeypatch.setattr(remaining, "get_api_json", lambda *a, **k: payload)
    assert not load("promiedos", on_error="collect").complete


def test_promiedos_timezone_required_and_pregame_score_null(monkeypatch, promiedos):
    monkeypatch.setattr(remaining, "get_api_json", lambda *a, **k: promiedos)
    assert not load("promiedos", source_timezone=None, on_error="collect").complete
    promiedos["leagues"][0]["games"][0]["status"]["enum"] = 1
    assert load("promiedos").match_records[0].home_score is None
    promiedos["leagues"][0]["games"][0]["start_time"] = "17-08-2024 19:00"
    assert not load("promiedos", on_error="collect").complete


def test_besoccer_filter_offset_dates_and_adjacent_fixtures(monkeypatch):
    text = BE_HTML.replace(
        "</body>",
        BE_HTML.split("<body>")[1]
        .split("</body>")[0]
        .replace("match-123", "match-124")
        .replace("2024-08-16T", "2024-08-17T")
        + "</body>",
    )
    monkeypatch.setattr(remaining, "get_text", lambda *a, **k: text)
    result = load("besoccer")
    assert result.complete and len(result.match_records) == 1
    assert result.match_records[0].kickoff.hour == 18
    assert result.match_records[0].home_team_id == "10"
    assert not load(
        "besoccer", start_date="2024-08-17", end_date="2024-08-17", on_error="collect"
    ).complete


@pytest.mark.parametrize("text", ["<html>Maintenance</html>", "<title>Client Challenge</title>"])
def test_besoccer_block_or_missing_listing_is_error(monkeypatch, text):
    monkeypatch.setattr(remaining, "get_text", lambda *a, **k: text)
    assert not load("besoccer", on_error="collect").complete


def test_besoccer_standings_only_uses_native_team_ids(monkeypatch):
    row = """<tr class="row-body"><td>1</td>
        <td><img src="https://cdn.resfu.com/img_data/equipos/10.png"></td>
        <td><span class="team-name">Home</span></td>
        <td>3</td><td>1</td><td>1</td><td>0</td><td>0</td><td>2</td><td>0</td><td>2</td></tr>"""
    urls = []
    monkeypatch.setattr(
        remaining, "get_text", lambda url, **k: urls.append(url) or f"<table>{row}</table>"
    )
    result = load("besoccer", tables=["standings"], start_date=None, end_date=None)
    assert result.complete and result.metadata.coverage_scope == "season"
    assert result.standing_records[0].team_id == "10"
    assert result.standing_records[0].points == 3
    assert urls == ["https://es.besoccer.com/competicion/clasificacion/premier_league/2024"]


@pytest.fixture
def tm_fetch():
    def fetch(url, **kwargs):
        if "/club/" in url:
            return {
                "data": {
                    "id": "281",
                    "name": "Home",
                    "baseDetails": {"primaryCompetitionId": "GB1"},
                }
            }
        if "market-value-history" in url:
            return {
                "data": {
                    "history": [
                        {
                            "playerId": "9",
                            "clubId": "281",
                            "seasonId": 2024,
                            "marketValue": {
                                "determined": "2024-08-01",
                                "value": 100,
                                "currency": "EUR",
                            },
                        }
                    ]
                }
            }
        if "/transfer/" in url:
            return {
                "data": {
                    "history": {
                        "pending": [],
                        "terminated": [
                            {
                                "id": "t1",
                                "details": {
                                    "playerId": "9",
                                    "date": "2022-07-01",
                                    "fee": {"value": 0},
                                },
                                "transferSource": {"clubId": 1},
                                "transferDestination": {"clubId": 281},
                            }
                        ],
                    }
                }
            }
        return {
            "data": {
                "id": "9",
                "name": "Player",
                "clubAssignments": [{"clubId": 281}],
                "marketValueDetails": {"current": {"value": 100, "currency": "EUR"}},
            }
        }

    return fetch


def test_transfermarkt_all_entity_tables_and_storage(monkeypatch, tm_fetch, tmp_path):
    monkeypatch.setattr(providers, "get_api_json", tm_fetch)
    result = load(
        "transfermarkt", tables=["teams", "players", "market_values", "transfers"], player_ids=[9]
    )
    assert result.complete and result.metadata.coverage_scope == "entities"
    assert result.metadata.requested_club_ids == (
        "281",
    ) and result.metadata.requested_player_ids == ("9",)
    assert result.player_records[0].team_id == "281"
    assert result.market_value_records[0].currency == "EUR"
    assert result.transfer_records[0].fee == 0
    assert (
        result.transfer_records[0].source_date == "2022-07-01"
    )  # Full history, not a mislabeled season slice.
    pytest.importorskip("pandas")
    assert str(result.players.market_value.dtype) == "Int64"
    assert str(result.transfers.fee.dtype) == "Int64"
    pytest.importorskip("pyarrow")
    result.save(tmp_path / "snapshot")
    assert esd.open_dataset(tmp_path / "snapshot") == result


def test_transfermarkt_wrong_identity_and_partial_history_fail(monkeypatch, tm_fetch):
    monkeypatch.setattr(providers, "get_api_json", tm_fetch)
    assert not load("transfermarkt", league="XX1", on_error="collect").complete
    monkeypatch.setattr(providers, "get_api_json", lambda *a, **k: {"data": {"history": []}})
    assert not load(
        "transfermarkt", tables=["transfers"], club_ids=None, player_ids=[9], on_error="collect"
    ).complete
    monkeypatch.setattr(providers, "get_api_json", lambda *a, **k: {"data": {"id": "99"}})
    assert not load(
        "transfermarkt", tables=["players"], club_ids=None, player_ids=[9], on_error="collect"
    ).complete


@pytest.mark.parametrize("source", ["fbref", "goaloo", "promiedos", "besoccer", "transfermarkt"])
def test_new_providers_share_typed_tables_and_parquet_contract(
    monkeypatch, goaloo, promiedos, tm_fetch, tmp_path, source
):
    monkeypatch.setattr(
        providers,
        "get_api_json",
        lambda url, **k: goaloo if source == "goaloo" else tm_fetch(url, **k),
    )
    monkeypatch.setattr(remaining, "get_api_json", lambda *a, **k: promiedos)
    monkeypatch.setattr(
        remaining, "get_text", lambda *a, **k: FBREF_HTML if source == "fbref" else BE_HTML
    )
    result = load(source)
    assert result.complete
    assert esd.check_dataset_compatibility(result, result).schema_compatible
    pytest.importorskip("pandas")
    empty_teams = esd.normalized_to_dataframe([], table="teams")
    assert result.teams.dtypes.equals(empty_teams.dtypes)
    if source != "transfermarkt":
        empty_matches = esd.normalized_to_dataframe([], table="matches")
        assert result.matches.dtypes.equals(empty_matches.dtypes)
    pytest.importorskip("pyarrow")
    result.save(tmp_path / source)
    assert esd.open_dataset(tmp_path / source) == result


def test_transfermarkt_cache_is_shared_across_repeated_entity_queries(
    monkeypatch, tm_fetch, tmp_path
):
    monkeypatch.setattr(providers, "get_api_json", tm_fetch)
    options = {
        "tables": ["teams", "players", "market_values", "transfers"],
        "player_ids": [9],
        "cache_dir": tmp_path,
    }
    first = load("transfermarkt", **options)
    monkeypatch.setattr(providers, "get_api_json", lambda *a, **k: pytest.fail("Unexpected HTTP"))
    second = load("transfermarkt", **options)
    assert first.complete and second.complete and len(second.metadata.cached_tasks) == 4
    assert first.metadata.response_fetched_at == second.metadata.response_fetched_at


@pytest.mark.parametrize(
    "source,options",
    [
        ("goaloo", {"source_season": None}),
        ("goaloo", {"source_season": "2025-2026"}),
        ("goaloo", {"season_id": 1}),
        ("goaloo", {"club_ids": [1]}),
        ("fbref", {"start_date": None}),
        ("promiedos", {"end_date": "2024-08-15"}),
        ("besoccer", {"start_date": "2024-8-16"}),
        ("fbref", {"tables": ["standings"]}),
        ("transfermarkt", {"club_ids": []}),
        ("transfermarkt", {"club_ids": [281, 281]}),
        ("transfermarkt", {"tables": ["matches"]}),
        ("transfermarkt", {"tables": ["players"], "club_ids": None}),
    ],
)
def test_invalid_selections_fail_before_network(monkeypatch, source, options):
    monkeypatch.setattr(
        providers, "get_api_json", lambda *a, **k: pytest.fail("Unexpected request")
    )
    monkeypatch.setattr(remaining, "get_text", lambda *a, **k: pytest.fail("Unexpected request"))
    with pytest.raises(ValueError):
        load(source, **options)


def test_new_provider_callback_error_is_not_wrapped(monkeypatch, goaloo):
    monkeypatch.setattr(providers, "get_api_json", lambda *a, **k: goaloo)

    def callback(task):
        raise RuntimeError("User callback")

    with pytest.raises(RuntimeError, match="User callback"):
        load("goaloo", progress=callback, on_error="collect")


def test_failed_date_is_preserved_alongside_successful_dates(monkeypatch, promiedos):
    def fetch(url, **kwargs):
        if "2024-08-17" in url:
            raise SourceError("Source unavailable")
        return promiedos

    monkeypatch.setattr(remaining, "get_api_json", fetch)
    result = load("promiedos", end_date="2024-08-17", on_error="collect")
    assert not result.complete and len(result.match_records) == 1
    assert result.metadata.successful_tasks == ("matches:2024-08-16",)
    assert len(result.errors) == 1

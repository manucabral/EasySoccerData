"""Live examples handle empty responses and source failures without network access."""

import runpy
from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

import esd
from esd.exceptions import SourceBlocked

ROOT = Path(__file__).resolve().parent.parent
PROVIDERS = (
    "sofascore",
    "fbref",
    "promiedos",
    "espn",
    "scores365",
    "goaloo",
    "besoccer",
    "understat",
    "transfermarkt",
)
EXAMPLES = [
    path for provider in PROVIDERS for path in sorted((ROOT / "examples" / provider).glob("*.py"))
]


def load(path):
    return runpy.run_path(str(ROOT / "examples" / path))


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda path: str(path.relative_to(ROOT)))
def test_importing_live_example_does_not_construct_clients(monkeypatch, path):
    forbidden = Mock(side_effect=AssertionError("Client constructed while importing example"))
    for name in (
        "SofascoreClient",
        "FBrefClient",
        "PromiedosClient",
        "ESPNClient",
        "Scores365Client",
        "GoalooClient",
        "BeSoccerClient",
        "UnderstatClient",
        "TransfermarktClient",
    ):
        monkeypatch.setattr(esd, name, forbidden)
    monkeypatch.setattr("esd.goaloo.GoalooClient", forbidden)
    monkeypatch.setattr("esd.sofascore.SofascoreClient", forbidden)
    runpy.run_path(str(path))
    forbidden.assert_not_called()


def client_for(monkeypatch, name):
    client = MagicMock()
    client.__enter__.return_value = client
    factory = Mock(return_value=client)
    monkeypatch.setattr(esd, name, factory)
    provider = {"SofascoreClient": "sofascore", "FBrefClient": "fbref"}[name]
    monkeypatch.setattr(f"esd.{provider}.{name}", factory)
    return client


@pytest.mark.parametrize(
    ("path", "method", "name"),
    [
        ("sofascore/get_live_matchs.py", "get_events", "SofascoreClient"),
        ("sofascore/match_lineups.py", "get_events", "SofascoreClient"),
        ("sofascore/team_players.py", "search", "SofascoreClient"),
        ("sofascore/search_tournament.py", "search", "SofascoreClient"),
        ("sofascore/search_matchs.py", "search", "SofascoreClient"),
        ("sofascore/tournament_bracket.py", "get_tournament_brackets", "SofascoreClient"),
        ("sofascore/tournament_standing.py", "get_tournament_standings", "SofascoreClient"),
        ("fbref/match_details.py", "get_matchs", "FBrefClient"),
    ],
)
def test_empty_selection_exits_and_closes_client(monkeypatch, path, method, name, capsys):
    client = client_for(monkeypatch, name)
    getattr(client, method).return_value = []
    assert load(path)["main"]() == 0
    client.__exit__.assert_called_once()
    assert capsys.readouterr().out


@pytest.mark.parametrize(
    ("path", "name", "method"),
    [
        ("sofascore/get_live_matchs.py", "SofascoreClient", "get_events"),
        ("fbref/match_details.py", "FBrefClient", "get_matchs"),
    ],
)
def test_source_block_reports_failure_and_closes_client(monkeypatch, path, name, method, capsys):
    client = client_for(monkeypatch, name)
    getattr(client, method).side_effect = SourceBlocked("Blocked sample")
    assert load(path)["main"]() == 1
    client.__exit__.assert_called_once()
    assert "SourceBlocked" in capsys.readouterr().err


def test_live_match_without_statistics(monkeypatch, capsys):
    client = client_for(monkeypatch, "SofascoreClient")
    client.get_events.return_value = [esd.sofascore.Event(id=1)]
    client.get_match_stats.return_value = esd.sofascore.MatchStats()
    assert load("sofascore/get_live_matchs.py")["main"]() == 0
    assert "No match statistics" in capsys.readouterr().out


def test_live_match_without_lineups(monkeypatch, capsys):
    client = client_for(monkeypatch, "SofascoreClient")
    client.get_events.return_value = [esd.sofascore.Event(id=1)]
    client.get_match_lineups.return_value = esd.sofascore.Lineups()
    assert load("sofascore/match_lineups.py")["main"]() == 0
    assert capsys.readouterr().out.count("No lineup") == 2


def test_team_search_selects_native_id_and_keeps_unknown_dates(monkeypatch, capsys):
    client = client_for(monkeypatch, "SofascoreClient")
    client.search.return_value = [esd.sofascore.Team(id=999), esd.sofascore.Team(id=44)]
    client.get_team_players.return_value = [
        esd.sofascore.Player(date_of_birth=None, contract_until=0)
    ]
    assert load("sofascore/team_players.py")["main"]() == 0
    client.get_team_players.assert_called_once_with(44)
    output = capsys.readouterr().out
    assert "Unknown" in output and "1970" not in output


def test_tournament_search_selects_native_id(monkeypatch):
    client = client_for(monkeypatch, "SofascoreClient")
    client.search.return_value = [esd.sofascore.Tournament(id=999), esd.sofascore.Tournament(id=7)]
    client.get_tournament_seasons.return_value = []
    assert load("sofascore/search_tournament.py")["main"]() == 0
    client.get_tournament_seasons.assert_called_once_with(7)


@pytest.mark.parametrize(
    "path", ["promiedos/tournament_stages.py", "promiedos/tournament_matches.py"]
)
def test_missing_tournament_stage_does_not_query_matches(monkeypatch, path):
    client = Mock()
    client.get_tournament.return_value = esd.promiedos.Tournament()
    monkeypatch.setattr(esd, "PromiedosClient", Mock(return_value=client))
    assert load(path)["main"]() == 0
    client.get_tournament_matchs.assert_not_called()


@pytest.mark.parametrize("choice", ["-1", "9", "invalid"])
def test_live_table_rejects_invalid_indices_and_closes(monkeypatch, choice):
    client = client_for(monkeypatch, "SofascoreClient")
    client.get_events.return_value = []
    answers = iter((choice, "q"))
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    assert load("sofascore/live_table.py")["main"]() == 0
    client.get_match_stats.assert_not_called()
    client.__exit__.assert_called_once()


def test_live_table_closes_on_eof(monkeypatch):
    client = client_for(monkeypatch, "SofascoreClient")
    client.get_events.return_value = []

    def eof(_):
        raise EOFError

    monkeypatch.setattr("builtins.input", eof)
    assert load("sofascore/live_table.py")["main"]() == 0
    client.__exit__.assert_called_once()


def test_match_search_prints_unknown_time_for_each_fixture(monkeypatch, capsys):
    client = client_for(monkeypatch, "SofascoreClient")
    status = esd.sofascore.Status(type=esd.sofascore.StatusType.NOT_STARTED)
    client.search.return_value = [
        esd.sofascore.Event(id=1, status=status),
        esd.sofascore.Event(id=2, status=status, start_timestamp=None),
    ]
    assert load("sofascore/search_matchs.py")["main"]() == 0
    assert capsys.readouterr().out.count("Start time: Unknown") == 2


def test_fbref_details_use_summary_when_simple_rows_are_absent(monkeypatch, capsys):
    from esd.fbref.types.details import MatchDetails, PlayerStatsTableDetails, PlayerSummaryRow

    client = client_for(monkeypatch, "FBrefClient")
    client.get_matchs.return_value = [esd.fbref.Match(id="1", id_type="matches")]
    client.get_match_details.return_value = MatchDetails(
        home_players=PlayerStatsTableDetails(
            summary=[PlayerSummaryRow(player="Sample player", goals=0)]
        ),
    )
    assert load("fbref/match_details.py")["main"]() == 0
    assert "Sample player" in capsys.readouterr().out

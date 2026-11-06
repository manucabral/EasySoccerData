"""Tests for esd.sofascore parsers, endpoints and types."""

from esd.sofascore.endpoints import SofascoreEndpoints
from esd.sofascore.types import (
    PlayerAttributes,
    StatusType,
    parse_event,
    parse_player,
    parse_top_players_match,
)


def test_player_attributes_default_factory():
    first = PlayerAttributes()
    second = PlayerAttributes()
    assert isinstance(first.overview, list)
    assert first.overview == []
    first.overview.append("x")
    assert second.overview == []


def test_parse_player_handles_null_market_value_raw():
    player = parse_player(
        {
            "id": 10,
            "name": "Lionel Messi",
            "proposedMarketValue": None,
            "proposedMarketValueRaw": None,
        }
    )
    assert player.id == 10
    assert player.market_value == 0


def test_parse_top_players_match_handles_null_potm():
    top = parse_top_players_match(
        {
            "playerOfTheMatch": None,
            "bestHomeTeamPlayers": [{"player": {"id": 1, "name": "Home Star"}}],
            "bestAwayTeamPlayers": [],
        }
    )
    assert top.best is not None
    assert len(top.home_team) == 1
    assert top.home_team[0].name == "Home Star"


def test_parse_event_elapsed_minutes_when_not_started():
    event = parse_event(
        {
            "id": 100,
            "startTimestamp": None,
            "status": {"type": "notstarted", "description": "Not started"},
            "time": {},
        }
    )
    assert event.status.type == StatusType.NOT_STARTED
    assert event.total_elapsed_minutes == 0
    assert event.current_elapsed_minutes == 0


def test_search_endpoint_url_encodes_query():
    endpoints = SofascoreEndpoints()
    url = endpoints.search_endpoint("Real Madrid & Co", "all")
    assert "Real%20Madrid%20%26%20Co" in url

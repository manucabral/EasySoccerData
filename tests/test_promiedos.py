"""Tests for esd.promiedos parsers and types."""

from esd.promiedos.types import (
    EventType,
    MatchStatus,
    parse_events,
    parse_match,
    parse_match_events,
    parse_match_stats,
    parse_players,
    parse_tournament,
)


def test_parse_events_does_not_mutate_input():
    payload = [
        {
            "name": "Liga Profesional",
            "id": "hc",
            "url_name": "liga-profesional",
            "games": [
                {
                    "id": "g1",
                    "start_time": "06-11-2026 20:00",
                    "status": {"enum": 2, "name": "Segundo Tiempo"},
                    "teams": [
                        {"name": "River Plate", "id": "1"},
                        {"name": "Boca Juniors", "id": "2"},
                    ],
                    "scores": [2, 1],
                }
            ],
        }
    ]
    first = parse_events("today", payload)
    second = parse_events("today", payload)
    assert len(first) == 1
    assert len(first[0].matches) == 1
    assert len(second[0].matches) == 1
    assert second[0].matches[0].home_team.name == "River Plate"
    assert second[0].matches[0].scores.home == 2
    assert second[0].matches[0].status.value == MatchStatus.IN_PROGRESS


def test_parse_match_handles_invalid_or_missing_start_time():
    match = parse_match({"id": "m1", "start_time": None})
    assert match.id == "m1"
    assert match.start_time == 0.0

    match_bad = parse_match({"id": "m2", "start_time": "not-a-date"})
    assert match_bad.start_time == 0.0


def test_parse_match_stats_and_events():
    stats = parse_match_stats(
        [
            {
                "name": "Posesión",
                "values": ["60%", "40%"],
                "percentages": [0.6, 0.4],
            }
        ]
    )
    assert stats.possession.home_value == "60%"
    assert stats.possession.away_value == "40%"

    events = parse_match_events(
        [
            {
                "rows": [
                    {
                        "events": [
                            {
                                "type": 15,
                                "time": "65'",
                                "team": 1,
                                "texts": ["Jugador Entra", "Jugador Sale"],
                            }
                        ]
                    }
                ]
            }
        ]
    )
    assert len(events.first_half) == 1
    item = events.first_half[0]
    assert item.event_type == EventType.SUBSTITUTION
    assert item.details.player_in == "Jugador Entra"
    assert item.details.player_out == "Jugador Sale"


def test_parse_tournament_and_players():
    tournament = parse_tournament(
        {
            "league": {"id": "fhc", "name": "Champions League"},
            "games": {
                "filters": [
                    {"key": "1", "name": "Fase 1", "selected": False},
                    {"key": "2", "name": "Octavos", "selected": True},
                ]
            },
        }
    )
    assert tournament.current_stage().id == "2"

    players = parse_players(
        {
            "lineups": {
                "teams": [
                    {
                        "formation": "4-3-3",
                        "starting": [{"name": "P1", "jersey_num": 10}],
                    },
                    {
                        "formation": "4-4-2",
                        "starting": [{"name": "P2", "jersey_num": 9}],
                    },
                ]
            }
        }
    )
    assert players.lineups.home_team.formation == "4-3-3"
    assert players.lineups.home_team.starting[0].name == "P1"

"""
Unit tests for 365Scores parsers and endpoints.
"""

from esd.scores365.endpoints import Scores365Endpoints
from esd.scores365.service import _normalize_date
from esd.scores365.types import (
    parse_game,
    parse_game_stats,
    parse_games,
    parse_search,
    parse_standings,
)


def test_normalize_date():
    assert _normalize_date("today") is None
    assert _normalize_date("2026-11-05") == "05/11/2026"
    assert _normalize_date("05/11/2026") == "05/11/2026"


def test_scores365_endpoints():
    ep = Scores365Endpoints()
    url = ep.games_allscores(start_date="05/11/2026", competition_id=72)
    assert "competitions=72" in url
    assert "startDate=05/11/2026" in url


def test_parse_game_and_events():
    payload = {
        "id": 4633224,
        "competitionId": 72,
        "competitionDisplayName": "Liga Profesional",
        "seasonNum": 228,
        "stageNum": 8,
        "roundNum": 15,
        "roundName": "Fecha",
        "startTime": "2026-10-31T21:30:00-03:00",
        "statusGroup": 4,
        "statusText": "Finalizado",
        "shortStatusText": "Final",
        "gameTime": 90.0,
        "members": [
            {
                "id": 347908,
                "athleteId": 418,
                "name": "Fernando Muslera",
                "jerseyNumber": 16,
            }
        ],
        "events": [
            {
                "competitorId": 7272,
                "playerId": 347908,
                "gameTime": 3.0,
                "addedTime": 0,
                "gameTimeDisplay": "3'",
                "isMajor": True,
                "eventType": {"id": 1, "name": "Gol", "subTypeName": "Gol de campo"},
            }
        ],
        "homeCompetitor": {
            "id": 867,
            "name": "Estudiantes",
            "score": 3.0,
            "redCards": 0,
            "isWinner": False,
            "lineups": {
                "status": "Confirmed",
                "formation": "4-3-3",
                "members": [
                    {
                        "id": 347908,
                        "status": 1,
                        "statusText": "Starting",
                        "position": {"name": "Portero"},
                        "ranking": 6.8,
                        "stats": [{"type": 30, "name": "Minutes", "value": "90'"}],
                    }
                ],
            },
        },
        "awayCompetitor": {"id": 7272, "name": "Instituto", "score": 3.0},
    }
    game = parse_game(payload)
    assert game.id == 4633224
    assert game.home_team.name == "Estudiantes"
    assert game.home_team.score == 3
    assert len(game.events) == 1
    assert game.events[0].player_name == "Fernando Muslera"
    assert game.home_lineup is not None
    assert len(game.home_lineup.starters) == 1
    assert game.home_lineup.starters[0].rating == 6.8


def test_parse_standings_stats_and_search():
    games = parse_games({"games": [{"id": 1, "homeCompetitor": {"name": "A"}}]})
    assert len(games) == 1

    st = parse_standings(
        {
            "standings": [
                {
                    "competitionId": 72,
                    "displayName": "Clausura",
                    "rows": [
                        {
                            "position": 1,
                            "competitor": {"id": 7272, "name": "Instituto"},
                            "gamePlayed": 15,
                            "gamesWon": 10,
                            "gamesEven": 3,
                            "gamesLost": 2,
                            "for": 24,
                            "against": 13,
                            "ratio": 11,
                            "points": 33,
                        }
                    ],
                }
            ]
        }
    )
    assert len(st) == 1
    assert st[0].rows[0].team.name == "Instituto"
    assert st[0].rows[0].points == 33

    stats = parse_game_stats(
        {
            "statistics": [
                {
                    "id": 10,
                    "name": "Posesión",
                    "competitorId": 7272,
                    "value": "52%",
                    "valuePercentage": 0.52,
                    "isMajor": True,
                }
            ]
        }
    )
    assert len(stats) == 1
    assert stats[0].percentage == 0.52

    sr = parse_search({"competitors": [{"id": 866, "name": "Boca Juniors"}]})
    assert len(sr.competitors) == 1
    assert sr.competitors[0].name == "Boca Juniors"

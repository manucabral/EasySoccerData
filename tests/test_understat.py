"""
Unit tests for Understat parsers and embedded script extractor.
"""

from esd.understat.service import extract_embedded_json
from esd.understat.types import (
    parse_league_matches,
    parse_match_shots,
    parse_players,
    parse_teams,
)


def test_extract_embedded_json():
    html_sample = r"""
    <script>
    var datesData = JSON.parse('\x5B\x7B\x22id\x22\x3A\x22101\x22\x7D\x5D');
    </script>
    """
    extracted = extract_embedded_json(html_sample)
    assert "datesData" in extracted
    assert extracted["datesData"][0]["id"] == "101"


def test_parse_understat_models():
    matches = parse_league_matches(
        {
            "dates": [
                {
                    "id": "26602",
                    "isResult": True,
                    "datetime": "2024-08-16 19:00:00",
                    "h": {
                        "id": "89",
                        "title": "Manchester United",
                        "short_title": "MUN",
                    },
                    "a": {"id": "228", "title": "Fulham", "short_title": "FUL"},
                    "goals": {"h": "1", "a": "0"},
                    "xG": {"h": "2.43", "a": "0.41"},
                    "forecast": {"w": "0.86", "d": "0.10", "l": "0.04"},
                }
            ]
        }
    )
    assert len(matches) == 1
    assert matches[0].id == 26602
    assert matches[0].home_xg == 2.43
    assert matches[0].home_goals == 1

    players = parse_players(
        [
            {
                "id": "8260",
                "player_name": "Erling Haaland",
                "team_title": "Manchester City",
                "games": "31",
                "time": "2555",
                "goals": "27",
                "assists": "5",
                "xG": "29.21",
                "xA": "4.32",
                "npxG": "23.12",
                "xGChain": "31.50",
                "xGBuildup": "3.10",
            }
        ]
    )
    assert len(players) == 1
    assert players[0].player_name == "Erling Haaland"
    assert players[0].xg == 29.21

    teams = parse_teams(
        {
            "teams": {
                "88": {
                    "id": "88",
                    "title": "Manchester City",
                    "history": [
                        {
                            "date": "2024-08-18",
                            "h_a": "a",
                            "result": "w",
                            "scored": 2,
                            "missed": 0,
                            "pts": 3,
                            "xG": 1.45,
                            "xGA": 0.92,
                            "npxG": 1.45,
                            "npxGA": 0.92,
                            "xpts": 1.81,
                        }
                    ],
                }
            }
        }
    )
    assert len(teams) == 1
    assert teams[0].title == "Manchester City"
    assert teams[0].history[0].xpts == 1.81

    shots = parse_match_shots(
        {
            "shots": {
                "h": [
                    {
                        "id": "584101",
                        "match_id": "26602",
                        "minute": "86",
                        "result": "Goal",
                        "X": "0.912",
                        "Y": "0.485",
                        "xG": "0.341",
                        "player": "Joshua Zirkzee",
                        "player_id": "8044",
                        "h_a": "h",
                    }
                ],
                "a": [],
            }
        }
    )
    assert len(shots) == 1
    assert shots[0].player == "Joshua Zirkzee"
    assert shots[0].x == 0.912
    assert shots[0].xg == 0.341

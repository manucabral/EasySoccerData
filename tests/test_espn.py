"""
Unit tests for ESPN parsers.
"""

import pytest

from esd.espn.service import _normalize_espn_date
from esd.espn.types import (
    parse_scoreboard,
    parse_standings,
    parse_summary,
    parse_teams,
)


def test_normalize_espn_date():
    assert _normalize_espn_date("today") is None
    assert _normalize_espn_date("2026-11-06") == "20261106"
    assert _normalize_espn_date("20261106") == "20261106"


@pytest.mark.parametrize("away_first", [False, True])
@pytest.mark.parametrize("identity", ["id", "homeAway", "both"])
def test_summary_assigns_teams_independently_of_order(away_first, identity):
    sides = ["home", "away"]
    if away_first:
        sides.reverse()
    groups = []
    rosters = []
    for side in sides:
        metadata = {}
        if identity in ("id", "both"):
            metadata["team"] = {"id": side}
        if identity in ("homeAway", "both"):
            metadata["homeAway"] = side
        groups.append({
            **metadata,
            "statistics": [{"name": "shots", "displayValue": side}],
        })
        rosters.append({
            **metadata,
            "roster": [{"athlete": {"id": side, "fullName": side}}],
        })
    summary = parse_summary({
        "header": {"competitions": [{"competitors": [
            {"homeAway": side, "team": {"id": side}} for side in sides
        ]}]},
        "boxscore": {"teams": groups},
        "rosters": rosters,
    })
    assert [stat.value for stat in summary.home_stats] == ["home"]
    assert [stat.value for stat in summary.away_stats] == ["away"]
    assert [player.id for player in summary.home_roster] == ["home"]
    assert [player.id for player in summary.away_roster] == ["away"]


def test_summary_uses_position_when_team_metadata_is_missing():
    summary = parse_summary({
        "boxscore": {"teams": [
            {"statistics": [{"displayValue": "12"}]},
            {"statistics": [{"displayValue": "7"}]},
        ]},
        "rosters": [
            {"roster": [{"athlete": {"id": "home"}}]},
            {"roster": [{"athlete": {"id": "away"}}]},
        ],
    })
    assert summary.home_stats[0].value == "12"
    assert summary.away_stats[0].value == "7"
    assert summary.home_roster[0].id == "home"
    assert summary.away_roster[0].id == "away"


def test_parse_espn_scoreboard_and_summary():
    matches = parse_scoreboard(
        {
            "events": [
                {
                    "id": "401841670",
                    "name": "Racing Club at Barracas Central",
                    "shortName": "RAC @ BAR",
                    "date": "2026-11-06T18:00Z",
                    "status": {
                        "type": {
                            "name": "STATUS_FINAL",
                            "state": "post",
                            "shortDetail": "FT",
                            "completed": True,
                        }
                    },
                    "competitions": [
                        {
                            "attendance": 12000,
                            "venue": {
                                "fullName": "Estadio Claudio Tapia",
                                "address": {"city": "Buenos Aires"},
                            },
                            "competitors": [
                                {
                                    "homeAway": "home",
                                    "score": "1",
                                    "winner": False,
                                    "team": {
                                        "id": "1",
                                        "displayName": "Barracas Central",
                                    },
                                },
                                {
                                    "homeAway": "away",
                                    "score": "2",
                                    "winner": True,
                                    "team": {"id": "2", "displayName": "Racing Club"},
                                },
                            ],
                        }
                    ],
                }
            ]
        }
    )
    assert len(matches) == 1
    assert matches[0].home_team.name == "Barracas Central"
    assert matches[0].away_team.score == 2
    assert matches[0].completed is True

    summary = parse_summary(
        {
            "header": {
                "id": "401841670",
                "competitions": [
                    {
                        "competitors": [
                            {
                                "homeAway": "home",
                                "score": "1",
                                "team": {"id": "1", "displayName": "Barracas Central"},
                            },
                            {
                                "homeAway": "away",
                                "score": "2",
                                "team": {"id": "2", "displayName": "Racing Club"},
                            },
                        ]
                    }
                ],
            },
            "boxscore": {
                "teams": [
                    {
                        "team": {"id": "1"},
                        "statistics": [
                            {
                                "name": "possessionPct",
                                "label": "Possession",
                                "displayValue": "45%",
                            }
                        ],
                    }
                ]
            },
            "rosters": [
                {
                    "homeAway": "home",
                    "roster": [
                        {
                            "starter": True,
                            "jersey": "1",
                            "position": {
                                "displayName": "Goalkeeper",
                                "abbreviation": "G",
                            },
                            "athlete": {"id": "10", "fullName": "Juan Espínola"},
                        }
                    ],
                }
            ],
            "keyEvents": [
                {
                    "id": "99",
                    "type": {"type": "goal", "text": "Goal"},
                    "text": "Goal scored",
                    "period": {"number": 1},
                    "clock": {"value": 24.0, "displayValue": "24'"},
                    "scoringPlay": True,
                    "team": {"id": "2"},
                }
            ],
            "commentary": [{"text": "Match ends."}],
        }
    )
    assert summary.event_id == "401841670"
    assert len(summary.home_stats) == 1
    assert len(summary.home_roster) == 1
    assert len(summary.key_events) == 1
    assert summary.key_events[0].scoring_play is True


def test_parse_espn_standings_and_teams():
    tables = parse_standings(
        {
            "children": [
                {
                    "id": "1",
                    "name": "Liga Profesional",
                    "abbreviation": "LPF",
                    "standings": {
                        "entries": [
                            {
                                "team": {"id": "5", "displayName": "Boca Juniors"},
                                "stats": [
                                    {"name": "rank", "value": 1.0},
                                    {"name": "gamesPlayed", "value": 15.0},
                                    {"name": "wins", "value": 10.0},
                                    {"name": "ties", "value": 3.0},
                                    {"name": "losses", "value": 2.0},
                                    {"name": "pointsFor", "value": 24.0},
                                    {"name": "pointsAgainst", "value": 10.0},
                                    {"name": "pointDifferential", "value": 14.0},
                                    {"name": "points", "value": 33.0},
                                ],
                            }
                        ]
                    },
                }
            ]
        }
    )
    assert len(tables) == 1
    assert tables[0].rows[0].team.name == "Boca Juniors"
    assert tables[0].rows[0].points == 33

    teams = parse_teams(
        {
            "sports": [
                {
                    "leagues": [
                        {
                            "teams": [
                                {"team": {"id": "5", "displayName": "Boca Juniors"}}
                            ]
                        }
                    ]
                }
            ]
        }
    )
    assert len(teams) == 1
    assert teams[0].name == "Boca Juniors"

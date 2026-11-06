"""Tests for esd.goaloo parsers and types."""

from esd.goaloo.types import (
    parse_asian_handicap,
    parse_goal_timings,
    parse_head_to_head,
    parse_league,
    parse_live_odds,
    parse_match_events,
    parse_match_score,
    parse_matches,
    parse_over_under,
    parse_recent_form,
    parse_standings,
    parse_standings_compact,
    parse_team_detail,
    parse_teams,
)


def test_parse_league_teams_and_standings():
    teams = parse_teams(
        [[10, "Arsenal", "", "ars.png", 0], [20, "Chelsea", "", "che.png", 0]]
    )
    league = parse_league(
        [36, "Premier League", "2025-2026", "#000", "pl.png", 38, 0, "EPL"]
    )
    assert league.id == 36
    assert league.short_name == "EPL"

    standings = parse_standings(
        [[0, 1, 10, 0, 10, 8, 1, 1, 22, 8, 14, 0, 0, 0, 0, 0, 25]],
        teams,
    )
    assert len(standings) == 1
    assert standings[0].team.name == "Arsenal"
    assert standings[0].points == 25

    compact = parse_standings_compact(
        [[1, 20, 5, 4, 1, 0, 10, 3, 7, 0, 0, 0, 0, 0, 13]],
        teams,
    )
    assert compact[0].team.name == "Chelsea"
    assert compact[0].points == 13


def test_parse_matches_and_tables():
    teams = parse_teams([[10, "Arsenal", "", "", 0], [20, "Chelsea", "", "", 0]])
    matches = parse_matches(
        {"R_1": [[999, 36, 0, "2026-08-15 15:00", 10, 20, "2-1", "1-0"]]},
        teams,
    )
    assert len(matches) == 1
    assert matches[0].home_score == 2
    assert matches[0].away_score == 1

    ou = parse_over_under([[1, 10, 10, 6, 1, 3, 60.0, 10.0, 30.0]], teams)
    assert ou[0].over == 6 and ou[0].over_pct == 60.0

    ah = parse_asian_handicap(
        [[1, 10, 10, 5, 1, 4, 1, 0, 0, 0, 60.0, 10.0, 30.0]],
        teams,
    )
    assert ah[0].win == 5 and ah[0].win_rate == 60.0

    gt = parse_goal_timings([[10, 1, 2, 0, 3, 1, 2, 4, 1, 5]], teams)
    assert len(gt[0].intervals) == 9
    assert gt[0].intervals[-1] == 5


def test_parse_h2h_recent_score_odds_events_and_team():
    h2h = parse_head_to_head("1,2,1|0,1,1|1,0,3")
    assert len(h2h.meetings) == 3
    assert h2h.home_wins == 1 and h2h.draws == 1 and h2h.away_wins == 1

    form = parse_recent_form("1,2,0#0,1,2|0,0,0#1,3,1")
    assert len(form.rounds) == 2
    assert form.rounds[0].home.goals_for == 2

    score = parse_match_score(
        {
            "ErrCode": 0,
            "Data": {
                "state": -1,
                "time": "90",
                "html": "<span class='score'>2</span><span class='score'>1</span><span title='Score 1st Half'>1-0</span>",
            },
        }
    )
    assert score.home_score == 2 and score.away_score == 1
    assert score.state_name == "Finished"

    odds = parse_live_odds(
        {
            "ErrCode": 0,
            "Data": {"ah": {"u": "0.95", "g": "-0.5", "d": "0.85"}},
        }
    )
    assert odds.asian_handicap.home == 0.95
    assert odds.asian_handicap.line == "-0.5"

    events = parse_match_events("[[1,23,10,101,102,1,'Saka','Odegaard',0,'',1,0,'']]")
    assert len(events) == 1
    assert events[0].type_name == "goal"
    assert events[0].player == "Saka"

    team = parse_team_detail(
        {
            "TeamInfo": [
                10,
                "Arsenal",
                "logo.png",
                "London",
                "Emirates",
                60000,
                "1886",
                "",
                "",
                "",
                "Premier League",
            ],
            "coach": [[1, "", "Mikel Arteta"]],
            "vanguard": [[101, 7, "Bukayo Saka", "", "saka.png"]],
            "TeamHonor": [["FA Cup", "2020"]],
        }
    )
    assert team.name == "Arsenal"
    assert team.coach == "Mikel Arteta"
    assert len(team.players) == 1
    assert team.players[0].position == "forward"

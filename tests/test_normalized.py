"""Provider adapters preserve identity, context and source values without pandas."""

from copy import deepcopy
from datetime import datetime, timezone

import pytest

from esd import normalize_match, normalize_standings, normalize_team
from esd.espn.types import ESPNMatch, ESPNStandingRow, ESPNStandingTable, ESPNTeam
from esd.scores365.types import Competitor, Game, StandingRow, StandingTable


def test_equivalent_matches_share_fields_but_keep_source_identity():
    espn = ESPNMatch(id="001", date="2026-11-06T18:00:00-03:00",
                     home_team=ESPNTeam(id="001", name="Home", score=0),
                     away_team=ESPNTeam(id="002", name="Away", score=None),
                     status_name="STATUS_SCHEDULED", status_detail="Scheduled")
    scores = Game(id=1, competition_id=72, season_num=228, stage_num=8,
                  start_time="2026-11-06T21:00Z",
                  home_team=Competitor(id=1, name="Home", score=0),
                  away_team=Competitor(id=2, name="Away", score=None),
                  status_group=1, status_text="Programado")
    originals = deepcopy((espn, scores))
    first = normalize_match(espn, competition_id="arg.1", season=2026)
    second = normalize_match(scores, season=2026)
    assert first.kickoff == second.kickoff == datetime(2026, 11, 6, 21, tzinfo=timezone.utc)
    assert first.home_team_name == second.home_team_name == "Home"
    assert first.home_score == second.home_score == 0
    assert first.away_score is second.away_score is None
    assert first.match_id == "001"
    assert second.match_id == "1"
    assert first.competition_id == "arg.1"
    assert second.competition_id == "72"
    assert first.season == second.season == "2026"
    assert first.source_season_id is None
    assert second.source_season_id == "228"
    assert second.stage_id == "8"
    assert first.source_status == "STATUS_SCHEDULED"
    assert second.source_status == "1"
    assert second.source_status_text == "Programado"
    assert (espn, scores) == originals


@pytest.mark.parametrize("team, source, expected_id", [
    (ESPNTeam(id="001", name="Same"), "espn", "001"),
    (Competitor(id=0, name="Same"), "scores365", "0"),
    (Competitor(), "scores365", None),
])
def test_team_ids_are_strings_without_name_matching(team, source, expected_id):
    normalized = normalize_team(team)
    assert normalized.source == source
    assert normalized.team_id == expected_id
    assert normalized.name == team.name


@pytest.mark.parametrize("match", [ESPNMatch(), Game()])
def test_missing_values_are_not_invented(match):
    normalized = normalize_match(match)
    assert normalized.match_id is None
    assert normalized.kickoff is None
    assert normalized.home_score is None
    assert normalized.away_score is None
    assert normalized.competition_id is None
    assert normalized.season is None


@pytest.mark.parametrize("date", ["2026-11-06T18:00:00", "invalid"])
def test_bad_or_naive_dates_raise(date):
    with pytest.raises(ValueError):
        normalize_match(ESPNMatch(date=date))


def test_standings_preserve_deductions_and_group_context():
    espn = ESPNStandingTable(id="group-a", name="Group A", rows=[
        ESPNStandingRow(team=ESPNTeam(id="001", name="Home"), rank=1, points=-2,
                        deductions=2, goal_diff=-3),
    ])
    scores = StandingTable(competition_id=72, season_num=228, stage_num=8,
                           display_name="Group A", rows=[
        StandingRow(team=Competitor(id=1, name="Home"), position=1, points=0,
                    group_num=2, goal_diff=-3),
    ])
    originals = deepcopy((espn, scores))
    first = normalize_standings(espn, competition_id="arg.1", season=2026)[0]
    second = normalize_standings(scores, season=2026)[0]
    assert first.rank == second.rank == 1
    assert first.goal_difference == second.goal_difference == -3
    assert first.table_id == "group-a"
    assert first.group_id is None
    assert first.deductions == 2
    assert first.points == -2
    assert second.points == 0
    assert second.deductions is None
    assert second.table_id is None
    assert second.group_id == "2"
    assert second.stage_id == "8"
    assert second.source_season_id == "228"
    assert first.season == second.season == "2026"
    assert (espn, scores) == originals


@pytest.mark.parametrize("table", [ESPNStandingTable(), StandingTable()])
def test_empty_standings_are_valid(table):
    assert normalize_standings(table) == []


@pytest.mark.parametrize("function, obj", [
    (normalize_match, Game(competition_id=72)),
    (normalize_standings, StandingTable(competition_id=72)),
])
def test_native_competition_id_cannot_be_replaced(function, obj):
    with pytest.raises(ValueError, match="competition_id conflicts"):
        function(obj, competition_id="other")


@pytest.mark.parametrize("function", [normalize_team, normalize_match, normalize_standings])
def test_unsupported_models_raise(function):
    with pytest.raises(TypeError, match="Unsupported"):
        function({})

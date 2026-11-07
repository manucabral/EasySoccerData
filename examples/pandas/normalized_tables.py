"""Combine ESPN and 365Scores sample records without network access.

Install EasySoccerData[pandas] first. Replace the sample models with client
results when fetching data. IDs identify entities only within each provider.
"""

import pandas as pd

from esd import normalize_match, normalize_standings, normalize_team, normalized_to_dataframe
from esd.espn.types import ESPNMatch, ESPNStandingRow, ESPNStandingTable, ESPNTeam
from esd.scores365.types import Competitor, Game, StandingRow, StandingTable

espn_team = ESPNTeam(id="001", name="Home", score=0)
scores_team = Competitor(id=1, name="Home", score=0)

espn_game = ESPNMatch(id="001", date="2026-11-06T18:00:00-03:00", home_team=espn_team)
scores_game = Game(id=1, competition_id=72, season_num=228,
                   start_time="2026-11-06T21:00Z", home_team=scores_team)

matches = normalized_to_dataframe([
    normalize_match(espn_game, competition_id="arg.1", season=2026),
    normalize_match(scores_game, season=2026),
], table="matches")
print(matches[["source", "match_id", "competition_id", "season", "kickoff", "home_score"]])

teams = normalized_to_dataframe([normalize_team(espn_team), normalize_team(scores_team)],
                                table="teams")
joined = matches.merge(teams, left_on=["source", "home_team_id"],
                       right_on=["source", "team_id"], validate="many_to_one")
print(joined[["source", "match_id", "name"]])

espn_table = ESPNStandingTable(id="group-a", name="Group A", rows=[
    ESPNStandingRow(team=espn_team, rank=1, points=3),
])
scores_table = StandingTable(competition_id=72, season_num=228, stage_num=8, rows=[
    StandingRow(team=scores_team, position=1, points=3, group_num=1),
])
standings = pd.concat([
    normalized_to_dataframe(normalize_standings(espn_table, competition_id="arg.1", season=2026),
                            table="standings"),
    normalized_to_dataframe(normalize_standings(scores_table, season=2026), table="standings"),
], ignore_index=True)
print(standings[["source", "table_id", "stage_id", "group_id", "team_name", "rank", "points"]])

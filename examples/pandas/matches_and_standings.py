"""Analyze sample ESPN models without network access.

Install the optional dependency with pip install "EasySoccerData[pandas]".
The same conversion works with ESPNClient.get_scoreboard() results and the
rows of each table returned by ESPNClient.get_standings().
"""

from esd import to_dataframe
from esd.espn.types import ESPNMatch, ESPNStandingRow, ESPNTeam

matches = [
    ESPNMatch(
        id="001",
        date="2026-11-06T18:00:00-03:00",
        completed=True,
        home_team=ESPNTeam(id="home", name="Home", score=2),
        away_team=ESPNTeam(id="away", name="Away", score=0),
    ),
    ESPNMatch(
        id="002",
        home_team=ESPNTeam(id="away", name="Away"),
        away_team=ESPNTeam(id="home", name="Home"),
    ),
]

games = to_dataframe(
    matches,
    flatten=True,
    convert_dtypes=True,
    dtypes={"id": "string", "home_team.score": "Int64", "away_team.score": "Int64"},
    datetime_columns={"date": None},
)
print(games[["id", "date", "home_team.name", "home_team.score", "away_team.score"]])

rows = [
    ESPNStandingRow(rank=1, team=ESPNTeam(id="home", name="Home"), points=3),
    ESPNStandingRow(rank=2, team=ESPNTeam(id="away", name="Away"), points=0),
]
standings = to_dataframe(rows, flatten=True, convert_dtypes=True)
print(standings.sort_values("rank")[["rank", "team.name", "points"]])

home_points = standings[["team.id", "points"]].rename(columns={"points": "home_points"})
print(games.merge(home_points, left_on="home_team.id", right_on="team.id",
                  how="left", validate="many_to_one")[["id", "home_team.name", "home_points"]])

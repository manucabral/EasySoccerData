"""Fetch Promiedos tournament stages, then print matches in the first stage.

Makes network requests when executed.
"""

from esd import PromiedosClient, PromiedosTypes

client = PromiedosClient()

# "fhc" is the ID of uefa champions league
tournament: PromiedosTypes.Tournament = client.get_tournament("fhc")

# get all stages
stages: list[PromiedosTypes.Stage] = tournament.stages

# print the stages
for stage in stages:
    print(stage.name, stage.selected)

# now we will use the first stage
stage = stages[0]
matches = client.get_tournament_matchs(tournament.league.id, stage.id)
for match in matches:
    print(match.home_team.name, "vs", match.away_team.name)

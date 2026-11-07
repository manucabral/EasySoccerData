"""Fetch a Promiedos tournament and print matches in its selected stage.

Makes network requests when executed.
"""

from esd import PromiedosClient, PromiedosTypes

client = PromiedosClient()

# "fhc" is the ID of uefa champions league
tournament: PromiedosTypes.Tournament = client.get_tournament("fhc")

# print some info
print(tournament.league.name, tournament.league.slug)

# Get the current stage for getting the matches
stage: PromiedosTypes.Stage = tournament.current_stage()
print("Current stage is", stage.name)

# Get the matches for the tournament
matches: list[PromiedosTypes.Match] = client.get_tournament_matchs(
    tournament.league.id, stage.id
)

# Print the matches
print("Matches:")
for match in matches:
    print(match.home_team.name, "vs", match.away_team.name)

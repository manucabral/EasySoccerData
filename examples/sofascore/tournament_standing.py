"""Fetch Sofascore standings for a selected Champions League season.

Makes network requests when executed.
"""

import esd


client = esd.SofascoreClient()

# Find tournament IDs with search() and season IDs with get_tournament_seasons().
uefa_tournament_id = 7
last_season_id = 61644

standings: list[esd.sofascore.Standing] = client.get_tournament_standings(
    uefa_tournament_id, last_season_id
)

# Select one returned standings table.
current_standing = standings[0]

for item in current_standing.items:
    print(f"{item.position}. {item.team.name} {item.points} points")
    print(
        f"Matches: {item.matches}Wins: {item.wins} Draws: {item.draws} Losses: {item.losses}"
    )

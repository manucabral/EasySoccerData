"""Fetch the first live Sofascore match and print formations and starting players.

Makes network requests when executed.
"""

import esd

client = esd.SofascoreClient()
matchs = client.get_events(live=True)
match = matchs[0]

print(match.away_team.name, "vs", match.home_team.name)

lineups = client.get_match_lineups(match.id)
print("Confirmed lineups:", lineups.confirmed)

print("FORMATION", match.home_team.name, ":", lineups.home.formation)
home_players = lineups.home.players
for player in home_players:
    info: esd.sofascore.Player = player.info
    if player.substitute:
        # ignore substitutes
        continue
    print(info.name, "|", info.position, "|", info.shirt_number)
    print("-------------------")

print("FORMATION", match.away_team.name, ":", lineups.away.formation)
away_players = lineups.away.players
for player in away_players:
    info: esd.sofascore.Player = player.info
    if player.substitute:
        # ignore substitutes
        continue
    print(info.name, "|", info.position, "|", player.info.jersey_number)
    print("-------------------")

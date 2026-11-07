"""Fetch Sofascore top-scorer rankings for a selected Champions League season.

Makes network requests when executed.
"""

from esd.sofascore import SofascoreClient

client = SofascoreClient()

uefacl_id = 7
last_season = 61644
top = client.get_tournament_top_players(uefacl_id, last_season)

for index, item in enumerate(top.goals):
    print(f"{index + 1}. {item.player.name} - {item.stat.value}")

# Other ranking categories are listed on TopTournamentPlayers.

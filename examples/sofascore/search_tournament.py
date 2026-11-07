"""Search Sofascore for UEFA tournaments and fetch seasons for a selected result.

Makes network requests when executed.
"""

import esd

client = esd.SofascoreClient()

# search for tournaments
tournaments: list[esd.sofascore.Tournament] = client.search(
    "uefa", entity=esd.sofascore.EntityType.TOURNAMENT
)

for tournament in tournaments:
    print(f"{tournament.id}, {tournament.name}, {tournament.slug}")
    print("---------------------------")

# selecting uefa champions league
uefa = tournaments[0]
seasons: list[esd.sofascore.Season] = client.get_tournament_seasons(uefa.id)

print("Seasons:")
for season in seasons:
    print(f"{season.id}, {season.name}")

"""Search Sofascore for Liverpool teams and print IDs, names and slugs.

Makes network requests when executed.
"""

import esd

client = esd.SofascoreClient()
teams: list[esd.sofascore.Team] = client.search(
    "Liverpool", entity=esd.sofascore.EntityType.TEAM
)

for team in teams:
    print(f"{team.id}, {team.name}, {team.slug}")
    print("---------------------------")

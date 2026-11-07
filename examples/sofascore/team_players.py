"""Fetch Liverpool's Sofascore squad and print positions, shirt numbers and contracts.

Makes network requests when executed.
"""

import esd
import datetime

client = esd.SofascoreClient()

teams: list[esd.sofascore.Team] = client.search(
    "Liverpool", entity=esd.sofascore.EntityType.TEAM
)
liverpool_team = teams[0]  # Liverpool FC
liverpool_players = client.get_team_players(liverpool_team.id)

for player in liverpool_players:
    print("---------------------------------")
    print(f"{player.name}, position {player.position}, number {player.jersey_number}")
    date_of_birth = datetime.datetime.fromtimestamp(player.date_of_birth).strftime(
        "%B %Y"
    )
    contract_until = datetime.datetime.fromtimestamp(player.contract_until).strftime(
        "%B %Y"
    )
    print(f"Date of birth: {date_of_birth}")
    print(f"Contract until: {contract_until}")

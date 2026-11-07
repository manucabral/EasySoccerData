"""Search Sofascore for Manchester United matches and print their status and times.

Makes network requests when executed.
"""

import esd
import datetime

client = esd.SofascoreClient()
matchs: list[esd.sofascore.Event] = client.search(
    "Manchester United", entity=esd.sofascore.EntityType.EVENT
)

for match in matchs:
    print(f"Match ID: {match.id}, Status: {match.status.description}")
    print(f"{match.home_team.name} vs {match.away_team.name}")
    if match.status.type == esd.sofascore.StatusType.NOT_STARTED:
        start_time = datetime.datetime.fromtimestamp(match.start_timestamp)
        print(f"Start time: {start_time}")
    print("--------------------")

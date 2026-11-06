"""
This example shows how to search for matchs.
In this case, we search for matchs that contain the word "Manchester United".

The output will be something like:

Match ID: 12436602, Status: Not started
Manchester United vs Manchester City
Start time: 2025-04-06 12:30:00
--------------------
Match ID: 12437005, Status: Not started
Manchester United vs Arsenal
Start time: 2025-03-09 13:30:00
--------------------
Match ID: 12436625, Status: Ended
Everton vs Manchester United
--------------------
.......
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

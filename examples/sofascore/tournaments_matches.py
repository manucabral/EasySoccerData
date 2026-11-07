"""Fetch upcoming and recent Sofascore tournament matches, including a second page.

Makes network requests when executed.
"""

from esd.sofascore import SofascoreClient

client = SofascoreClient()

uefacl_id = 7
last_season = 61644

# Get upcoming matches
events = client.get_tournament_events(uefacl_id, last_season, upcoming=True)
print("Upcoming matches")
for event in events:
    print(event.id, event.slug)

# Get last matches (page 0)
events = client.get_tournament_events(uefacl_id, last_season)
print("Last matches")
for event in events:
    print(event.id, event.slug)

# Fetch the second page of past matches.
events = client.get_tournament_events(uefacl_id, last_season, page=1)
print("Last last matches")
for event in events:
    print(event.id, event.slug)

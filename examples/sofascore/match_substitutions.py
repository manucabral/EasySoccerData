"""Fetch Sofascore match incidents and print substitutions.

Makes network requests when executed.
"""

from esd.sofascore import SofascoreClient, IncidentType

client = SofascoreClient()

# A. Madrid vs. Real Madrid
incidents = client.get_match_incidents(13511924)

for incident in incidents:

    if incident.type != IncidentType.SUBSTITUTION:
        continue

    print(
        f"{incident.player_out.short_name} is substituted by {incident.player_in.short_name} at {incident.time}'"
    )

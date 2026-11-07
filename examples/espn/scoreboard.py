"""Fetch an ESPN league scoreboard and print teams, scores, status and venue.

Makes network requests when executed.
"""

from __future__ import annotations

import esd

client = esd.ESPNClient()

# "arg.1" = Liga Profesional Argentina, "eng.1" = Premier League, "uefa.champions" = UCL
matches: list[esd.espn.ESPNMatch] = client.get_scoreboard("arg.1", date="today")

print(f"Found {len(matches)} matches in Liga Profesional Argentina (arg.1)\n")

for match in matches:
    if match.home_team.score is not None and match.away_team.score is not None:
        score = f"{match.home_team.score} - {match.away_team.score}"
    else:
        score = "vs"
    print(
        f"{match.home_team.name} {score} {match.away_team.name} "
        f"({match.status_detail}) | Venue: {match.venue_name}"
    )

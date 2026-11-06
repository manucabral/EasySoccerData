"""
In this example, we fetch the live/daily scoreboard for a league using
the ESPN client.

The output will be something like:

Found 5 matches in Liga Profesional Argentina (arg.1)

River Plate 2 - 1 Boca Juniors (FT) | Venue: Mâs Monumental
Racing Club 1 - 0 Independiente (FT) | Venue: Presidente Perón
...
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

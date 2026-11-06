"""
In this example, we fetch league matches with Expected Goals (xG) and
win probability forecasts from Understat.

The output will be something like:

Found 380 matches in EPL 2024

2024-08-16 19:00:00 | Manchester United 1 - 0 Fulham (xG: 2.43 - 0.41)
2024-08-17 11:30:00 | Ipswich 0 - 2 Liverpool (xG: 0.34 - 3.92)
...
"""

from __future__ import annotations

import esd

client = esd.UnderstatClient()

matches: list[esd.understat.UnderstatMatch] = client.get_league_matches("EPL", 2024)

print(f"Found {len(matches)} matches in EPL 2024\n")

for match in matches[:15]:
    if match.is_result and match.home_xg is not None and match.away_xg is not None:
        print(
            f"{match.datetime} | {match.home_team} {match.home_goals} - "
            f"{match.away_goals} {match.away_team} "
            f"(xG: {match.home_xg:.2f} - {match.away_xg:.2f})"
        )
    else:
        print(f"{match.datetime} | {match.home_team} vs {match.away_team}")

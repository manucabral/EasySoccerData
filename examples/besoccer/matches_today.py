"""
In this example, we fetch today's matches from BeSoccer and print the
competition, teams, score and match status/time.

The output will be something like:

Found 35 matches

[Primera División Argentina] River Plate 2 - 1 Boca Juniors (Finalizado)
[Premier League] Arsenal 3 - 0 Chelsea (Finalizado)
...
"""

from __future__ import annotations

import esd

client = esd.BeSoccerClient()

matches: list[esd.besoccer.BeSoccerMatch] = client.get_matches("today")

print(f"Found {len(matches)} matches\n")

for match in matches[:20]:
    if match.home_team.score is not None and match.away_team.score is not None:
        score = f"{match.home_team.score} - {match.away_team.score}"
    else:
        score = "vs"
    print(
        f"[{match.competition_name}] {match.home_team.name} {score} "
        f"{match.away_team.name} ({match.time_display})"
    )

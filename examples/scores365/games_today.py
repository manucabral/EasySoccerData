"""Fetch today's 365Scores games and print teams, scores and status.

Makes network requests when executed.
"""

from __future__ import annotations

import esd

client = esd.Scores365Client()

games: list[esd.scores365.Game] = client.get_games("today")

print(f"Found {len(games)} games\n")

for game in games[:20]:
    status = game.game_time_display or game.short_status_text or game.status_text
    if game.home_team.score is not None and game.away_team.score is not None:
        score = f"{game.home_team.score} - {game.away_team.score}"
    else:
        score = "vs"
    print(
        f"[{game.competition_name}] {game.home_team.name} {score} "
        f"{game.away_team.name} ({status})"
    )

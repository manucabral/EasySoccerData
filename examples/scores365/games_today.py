"""
In this example, we get today's games using the 365Scores client
and print the competition, teams, score and status.

The output will be something like:

Found 42 games

[Liga Profesional] River Plate 2 - 1 Boca Juniors (Finalizado)
[Premier League] Arsenal 3 - 0 Chelsea (Finalizado)
[LaLiga] Real Madrid None - None Barcelona (16:00)
...
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

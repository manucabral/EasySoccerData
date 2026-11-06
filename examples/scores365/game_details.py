"""
In this example, we get full match details (events, lineups and statistics)
from 365Scores using the first available game of the day.

The output will be something like:

Match: River Plate 2 - 1 Boca Juniors
Events:
  25' Gol - Franco Mastantuono
  44' Gol - Miguel Borja
  ...
Statistics:
  Posesión del balón (competitor 1234): 58%
  Remates totales (competitor 1234): 14
...
"""

from __future__ import annotations

import esd

client = esd.Scores365Client()

games = client.get_games("today")
if not games:
    print("No games found today.")
    raise SystemExit

game = client.get_game(games[0].id)
print(
    f"Match: {game.home_team.name} {game.home_team.score} - "
    f"{game.away_team.score} {game.away_team.name}"
)

if game.events:
    print("\nEvents:")
    for ev in game.events:
        minute = ev.time_display or f"{ev.minute}'"
        print(f"  {minute} {ev.event_type_name} - {ev.player_name}")

stats = client.get_game_stats(game.id)
if stats:
    print("\nStatistics:")
    for item in stats[:10]:
        print(f"  {item.name} (competitor {item.competitor_id}): {item.value}")

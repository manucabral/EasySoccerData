"""Fetch today's first 365Scores game and print its events and team statistics.

Makes network requests when executed.
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

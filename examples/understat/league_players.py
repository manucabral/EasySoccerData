"""Fetch Understat league player statistics and print goals, assists, xG and xA.

Makes network requests when executed.
"""

from __future__ import annotations

import esd

client = esd.UnderstatClient()

players: list[esd.understat.UnderstatPlayerStat] = client.get_league_players(
    "EPL", 2024
)
players.sort(key=lambda p: p.xg, reverse=True)

print(f"{'Player':<25} {'Team':<22} {'G':>3} {'xG':>6} {'A':>3} {'xA':>6}")
for player in players[:10]:
    print(
        f"{player.player_name:<25} {player.team_title:<22} "
        f"{player.goals:>3} {player.xg:>6.2f} "
        f"{player.assists:>3} {player.xa:>6.2f}"
    )

"""Fetch FBref league player statistics and print the leading scorers.

Makes network requests when executed.
"""

import esd

client = esd.FBrefClient(language="en")

# comp_id=9, league_slug="Premier-League" -> English Premier League on FBref
players: list[esd.fbref.LeaguePlayerStandard] = client.get_league_players(
    comp_id=9, league_slug="Premier-League"
)

players.sort(key=lambda p: p.goals, reverse=True)

print(f"{'Player':<25} {'Team':<22} {'G':>3} {'A':>3} {'xG':>6} {'MP':>3}")
for player in players[:10]:
    print(
        f"{player.player:<25} {player.team:<22} {player.goals:>3} "
        f"{player.assists:>3} {player.xg:>6.1f} {player.matches_played:>3}"
    )

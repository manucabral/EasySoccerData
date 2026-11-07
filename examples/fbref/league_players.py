"""Fetch FBref league player statistics and print the leading scorers.

Makes network requests when executed.
"""

import sys

import esd
from esd.exceptions import ESDException
from esd.fbref.exceptions import FBrefException


def main():
    try:
        with esd.FBrefClient(language="en") as client:
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
    except (ESDException, FBrefException) as exc:
        print(f"Source request failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

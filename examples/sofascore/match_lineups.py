"""Fetch the first live Sofascore match and print formations and starting players.

Makes network requests when executed.
"""

import sys

import esd
from esd.exceptions import ESDException


def main():
    try:
        with esd.SofascoreClient() as client:
            matchs = client.get_events(live=True)
            if not matchs:
                print("No live matches available.")
                return 0

            match = matchs[0]

            print(match.away_team.name, "vs", match.home_team.name)

            lineups = client.get_match_lineups(match.id)

            print("Confirmed lineups:", lineups.confirmed)

            for team, lineup in ((match.home_team, lineups.home), (match.away_team, lineups.away)):
                if lineup is None:
                    print(f"No lineup available for {team.name}.")
                    continue
                print("FORMATION", team.name, ":", lineup.formation)
                for player in lineup.players:
                    if player.substitute or player.info is None:
                        continue
                    info = player.info
                    print(info.name, "|", info.position, "|", info.jersey_number)
    except ESDException as exc:
        print(f"Source request failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

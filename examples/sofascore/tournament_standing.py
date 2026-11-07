"""Fetch Sofascore standings for a selected Champions League season.

Makes network requests when executed.
"""

import sys

import esd
from esd.exceptions import ESDException


def main():
    try:
        with esd.SofascoreClient() as client:
            uefa_tournament_id = 7

            last_season_id = 61644

            standings: list[esd.sofascore.Standing] = client.get_tournament_standings(
                uefa_tournament_id, last_season_id
            )

            if not standings:
                print("No standings available for this season.")
                return 0
            current_standing = standings[0]

            for item in current_standing.items:
                print(f"{item.position}. {item.team.name} {item.points} points")
                print(
                    f"Matches: {item.matches} Wins: {item.wins} Draws: {item.draws} Losses: {item.losses}"
                )
    except ESDException as exc:
        print(f"Source request failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

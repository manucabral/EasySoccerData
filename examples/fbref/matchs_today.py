"""Fetch today's FBref schedule and print scores, xG, rounds and venues.

Makes network requests when executed.
"""

import sys

import esd
from esd.exceptions import ESDException
from esd.fbref.exceptions import FBrefException


def main():
    try:
        with esd.FBrefClient(language="en") as client:
            matchs: list[esd.fbref.Match] = client.get_matchs()

            print(f"Found {len(matchs)} matches\n")

            for match in matchs:
                print(
                    f"{match.home_team} {match.home_score} - {match.away_score} {match.away_team}"
                )

                line = f"    xG: {match.home_xg} - {match.away_xg}"
                if match.round:
                    line += f" | Round: {match.round}"
                if match.gameweek:
                    line += f" | GW: {match.gameweek}"
                print(line)

                if match.start_time:
                    meta = f"    Time: {match.start_time}"
                    if match.venue:
                        meta += f" | Venue: {match.venue}"
                    print(meta)
                print()
    except (ESDException, FBrefException) as exc:
        print(f"Source request failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

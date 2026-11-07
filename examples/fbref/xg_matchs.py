"""Fetch an FBref schedule for a selected date and print scores, xG and notes.

Makes network requests when executed.
"""

import sys

import esd
from esd.exceptions import ESDException
from esd.fbref.exceptions import FBrefException


def main():
    try:
        with esd.FBrefClient(language="en") as client:
            matchs: list[esd.fbref.Match] = client.get_matchs(date="2025-03-11")

            for match in matchs:
                print(
                    f"{match.home_team} {match.home_score} - {match.away_score} {match.away_team}"
                )
                print(f"xG: {match.home_xg} - {match.away_xg}")
                if match.notes:
                    print(f"Notes: {match.notes}")
                print()
    except (ESDException, FBrefException) as exc:
        print(f"Source request failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

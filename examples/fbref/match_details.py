"""Fetch today's FBref schedule, then print player tables for the first match report.

Makes network requests when executed.
"""

import sys

import esd
from esd.exceptions import ESDException
from esd.fbref.exceptions import FBrefException


def main():
    try:
        with esd.FBrefClient(language="en") as client:
            matchs = client.get_matchs()

            match = next((m for m in matchs if m.id and m.id_type == "matches"), None)

            if match is None:
                print("No matches with an FBref report available today.")
                return 0

            details = client.get_match_details(match.id)

            print(f"Match: {match.home_team} - {match.away_team}\n")

            for label, table in [("Home", details.home_players), ("Away", details.away_players)]:
                print(f"{label} players:")
                if table is None:
                    print("No player table available.")
                    continue
                print(f"    {'Player':<25} {'Min':>4} {'G':>2} {'A':>2} {'Sh':>3} {'SoT':>3}")
                for row in (table.rows or table.summary)[:11]:
                    print(
                        f"    {row.player:<25} {row.minutes:>4} {row.goals:>2} "
                        f"{row.assists:>2} {row.shots:>3} {row.shots_on_target:>3}"
                    )
                print()
    except (ESDException, FBrefException) as exc:
        print(f"Source request failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

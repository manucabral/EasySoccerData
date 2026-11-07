"""Fetch 365Scores competition standings and print the first ten rows.

Makes network requests when executed.
"""

from __future__ import annotations

import sys

import esd
from esd.exceptions import ESDException


def main():
    try:
        client = esd.Scores365Client()

        tables: list[esd.scores365.StandingTable] = client.get_standings(72)

        for table in tables:
            title = table.display_name or f"Competition {table.competition_id}"
            print(f"{title} (Season {table.season_num})")
            print(
                f"{'Pos':>3}  {'Team':<24} {'PJ':>3} {'G':>3} {'E':>3} {'P':>3} {'DG':>4} {'PTS':>4}"
            )
            for row in table.rows[:10]:
                print(
                    f"{row.position:>3}  {row.team.name:<24} {row.played:>3} "
                    f"{row.won:>3} {row.drawn:>3} {row.lost:>3} "
                    f"{row.goal_diff:>+4} {row.points:>4}"
                )
            print()
    except ESDException as exc:
        print(f"Source request failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

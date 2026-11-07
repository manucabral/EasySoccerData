"""Fetch BeSoccer competition standings and print the first fifteen rows.

Makes network requests when executed.
"""

from __future__ import annotations

import sys

import esd
from esd.exceptions import ESDException


def main():
    try:
        client = esd.BeSoccerClient()

        rows: list[esd.besoccer.BeSoccerStandingRow] = client.get_standings("torneo_final")

        print(f"{'Pos':>3}  {'Team':<24} {'PJ':>3} {'G':>3} {'E':>3} {'P':>3} {'DG':>4} {'PTS':>4}")

        for row in rows[:15]:
            print(
                f"{row.position:>3}  {row.team.name:<24} {row.played:>3} "
                f"{row.won:>3} {row.drawn:>3} {row.lost:>3} "
                f"{row.goal_diff:>+4} {row.points:>4}"
            )
    except ESDException as exc:
        print(f"Source request failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

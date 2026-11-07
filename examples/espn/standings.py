"""Fetch ESPN league standings and print team ranks and points.

Makes network requests when executed.
"""

from __future__ import annotations

import esd

client = esd.ESPNClient()

tables: list[esd.espn.ESPNStandingTable] = client.get_standings("arg.1")

for table in tables:
    print(table.name)
    print(f"{'Pos':>3}  {'Team':<24} {'PJ':>3} {'G':>3} {'E':>3} {'P':>3} {'DG':>4} {'PTS':>4}")
    for row in table.rows[:10]:
        print(
            f"{row.rank:>3}  {row.team.name:<24} {row.played:>3} "
            f"{row.won:>3} {row.drawn:>3} {row.lost:>3} "
            f"{row.goal_diff:>+4} {row.points:>4}"
        )
    print()

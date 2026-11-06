"""
In this example, we fetch the standings table of a league using the ESPN client.

The output will be something like:

2025 Argentine Liga Profesional
Pos  Team                      PJ   G   E   P   DG  PTS
  1  Vélez Sarsfield           27  14   9   4  +22   51
  2  Talleres                  27  13   9   5  +12   48
...
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

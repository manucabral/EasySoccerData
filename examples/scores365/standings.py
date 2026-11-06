"""
In this example, we get the standings tables of a competition
using the 365Scores client and print the top rows.

The output will be something like:

Liga Profesional (Season 2025)
Pos  Team                      PJ   G   E   P   DG  PTS
  1  Vélez Sarsfield           27  14   9   4  +22   51
  2  Talleres                  27  13   9   5  +12   48
  3  Racing Club               27  14   4   9  +16   46
...
"""

from __future__ import annotations

import esd

client = esd.Scores365Client()

# 72 = Liga Profesional Argentina on 365Scores
tables: list[esd.scores365.StandingTable] = client.get_standings(72)

for table in tables:
    title = table.display_name or f"Competition {table.competition_id}"
    print(f"{title} (Season {table.season_num})")
    print(f"{'Pos':>3}  {'Team':<24} {'PJ':>3} {'G':>3} {'E':>3} {'P':>3} {'DG':>4} {'PTS':>4}")
    for row in table.rows[:10]:
        print(
            f"{row.position:>3}  {row.team.name:<24} {row.played:>3} "
            f"{row.won:>3} {row.drawn:>3} {row.lost:>3} "
            f"{row.goal_diff:>+4} {row.points:>4}"
        )
    print()

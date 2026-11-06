"""
In this example, we fetch the shotmap (pitch coordinates X, Y and xG)
for a single match on Understat.

The output will be something like:

Found 24 shots

12' [h] Bruno Fernandes - SavedShot (xG: 0.34, X: 0.88, Y: 0.49)
87' [h] Joshua Zirkzee - Goal (xG: 0.12, X: 0.91, Y: 0.52)
...
"""

from __future__ import annotations

import esd

client = esd.UnderstatClient()

shots: list[esd.understat.UnderstatShot] = client.get_match_shots(26602)

print(f"Found {len(shots)} shots\n")

for shot in shots:
    print(
        f"{shot.minute:>2}' [{shot.home_away}] {shot.player} - {shot.result} "
        f"(xG: {shot.xg:.2f}, X: {shot.x:.2f}, Y: {shot.y:.2f})"
    )

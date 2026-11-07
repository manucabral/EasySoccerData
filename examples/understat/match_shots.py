"""Fetch Understat shots for a match and print outcomes, source coordinates and xG.

Makes network requests when executed.
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

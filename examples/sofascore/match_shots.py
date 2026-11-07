"""Fetch shots for a Sofascore match and print player, xG, body part and minute.

Makes network requests when executed.
"""

from esd import SofascoreClient, SofascoreTypes

client = SofascoreClient()

match_id = 13511931  # PSG vs Liverpool (first match)
shots: list[SofascoreTypes.Shot] = client.get_match_shots(match_id)

for shot in shots:
    print(shot.player.short_name, shot.xg, shot.xg_got, shot.body_part, shot.time)

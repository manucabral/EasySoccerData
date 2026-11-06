"""
In this example, we fetch a player's transfer history from Transfermarkt.

The output will be something like:

Transfers for player 28003:
  23/24 (2023-07-15): Club 583 -> Club 69261 | Fee: free transfer | MV: €35.00m
  21/22 (2021-08-10): Club 131 -> Club 583   | Fee: free transfer | MV: €80.00m
...
"""

from __future__ import annotations

import esd

client = esd.TransfermarktClient()

transfers: list[esd.transfermarkt.TMTransfer] = client.get_player_transfers(28003)

print("Transfers for player 28003:")
for tr in transfers:
    print(
        f"  {tr.season} ({tr.date}): Club {tr.from_club_id} -> Club {tr.to_club_id} "
        f"| Fee: {tr.fee_display} | MV: {tr.market_value_display}"
    )

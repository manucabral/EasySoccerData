"""Fetch a Transfermarkt player's transfer history and print clubs, fees and valuations.

Makes network requests when executed.
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

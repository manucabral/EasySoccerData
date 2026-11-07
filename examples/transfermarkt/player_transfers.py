"""Fetch a Transfermarkt player's transfer history and print clubs, fees and valuations.

Makes network requests when executed.
"""

from __future__ import annotations

import sys

import esd
from esd.exceptions import ESDException


def main():
    try:
        client = esd.TransfermarktClient()

        transfers: list[esd.transfermarkt.TMTransfer] = client.get_player_transfers(28003)

        print("Transfers for player 28003:")

        for tr in transfers:
            print(
                f"  {tr.season} ({tr.date}): Club {tr.from_club_id} -> Club {tr.to_club_id} "
                f"| Fee: {tr.fee_display} | MV: {tr.market_value_display}"
            )
    except ESDException as exc:
        print(f"Source request failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Fetch a Transfermarkt player profile and print recent market-value history.

Makes network requests when executed.
"""

from __future__ import annotations

import sys

import esd
from esd.exceptions import ESDException


def main():
    try:
        client = esd.TransfermarktClient()

        player: esd.transfermarkt.TMPlayer = client.get_player(28003)

        print(f"Player: {player.name} (ID: {player.id})")

        print(f"Position: {player.position} | Age: {player.age} | Foot: {player.preferred_foot}")

        print(f"Current Market Value: {player.market_value_display}\n")

        history: list[esd.transfermarkt.TMMarketValueEntry] = (
            client.get_player_market_value_history(28003)
        )

        print("Market Value History (latest 5):")

        for entry in history[-5:]:
            print(f"  {entry.date}: {entry.display} (age {entry.age})")
    except ESDException as exc:
        print(f"Source request failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Fetch a Transfermarkt club profile and search for players, clubs and competitions.

Makes network requests when executed.
"""

from __future__ import annotations

import sys

import esd
from esd.exceptions import ESDException


def main():
    try:
        client = esd.TransfermarktClient()

        club: esd.transfermarkt.TMClub = client.get_club(281)

        print(f"Club: {club.name} ({club.abbreviation})")

        print(f"Squad Size: {club.squad_size} | Average Age: {club.average_age}")

        print(f"Total Market Value: {club.current_market_value_display}\n")

        results: list[esd.transfermarkt.TMSearchItem] = client.search("Messi")

        print("Search results for 'Messi':")

        for item in results[:5]:
            print(f"  [{item.entity_type}] {item.name} (ID: {item.id})")
    except ESDException as exc:
        print(f"Source request failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

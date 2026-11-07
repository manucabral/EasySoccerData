"""Fetch a Transfermarkt club profile and search for players, clubs and competitions.

Makes network requests when executed.
"""

from __future__ import annotations

import esd

client = esd.TransfermarktClient()

# 281 = Manchester City on Transfermarkt
club: esd.transfermarkt.TMClub = client.get_club(281)
print(f"Club: {club.name} ({club.abbreviation})")
print(f"Squad Size: {club.squad_size} | Average Age: {club.average_age}")
print(f"Total Market Value: {club.current_market_value_display}\n")

results: list[esd.transfermarkt.TMSearchItem] = client.search("Messi")
print("Search results for 'Messi':")
for item in results[:5]:
    print(f"  [{item.entity_type}] {item.name} (ID: {item.id})")

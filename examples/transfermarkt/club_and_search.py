"""
In this example, we fetch a club's profile and squad valuation summary
from Transfermarkt, as well as searching for entities by name.

The output will be something like:

Club: Manchester City (MCI)
Squad Size: 24 | Average Age: 26.8
Total Market Value: €1.26bn

Search results for 'Messi':
  [player] Lionel Messi (ID: 28003)
...
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

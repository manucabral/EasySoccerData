"""
In this example, we fetch a player's profile, current market value and
historical market value progression from Transfermarkt.

The output will be something like:

Player: Lionel Messi (ID: 28003)
Position: Right Winger | Age: 37 | Foot: left
Current Market Value: €20.00m

Market Value History (latest 5):
  2024-12-13: €20.00m (age 37)
  2024-06-13: €30.00m (age 36)
...
"""

from __future__ import annotations

import esd

client = esd.TransfermarktClient()

player: esd.transfermarkt.TMPlayer = client.get_player(28003)
print(f"Player: {player.name} (ID: {player.id})")
print(
    f"Position: {player.position} | Age: {player.age} | Foot: {player.preferred_foot}"
)
print(f"Current Market Value: {player.market_value_display}\n")

history: list[esd.transfermarkt.TMMarketValueEntry] = (
    client.get_player_market_value_history(28003)
)
print("Market Value History (latest 5):")
for entry in history[-5:]:
    print(f"  {entry.date}: {entry.display} (age {entry.age})")

"""Search 365Scores for competitions, teams and players.

Makes network requests when executed.
"""

from __future__ import annotations

import esd

client = esd.Scores365Client()

result: esd.scores365.SearchResult = client.search("River Plate")

print("Competitions:")
for comp in result.competitions[:5]:
    print(f"  [{comp.id}] {comp.name}")

print("\nTeams:")
for team in result.competitors[:5]:
    print(f"  [{team.id}] {team.name}")

print("\nAthletes:")
for athlete in result.athletes[:5]:
    print(f"  [{athlete.id}] {athlete.name}")

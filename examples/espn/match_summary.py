"""
In this example, we fetch the detailed summary (boxscore stats, rosters and
timeline events) of a match using the ESPN client.

The output will be something like:

Match: River Plate 2 - 1 Boca Juniors
Venue: Mâs Monumental

Home Stats:
  Possession: 58.2%
  Shots: 15
...
"""

from __future__ import annotations

import esd

client = esd.ESPNClient()

matches = client.get_scoreboard("arg.1", date="today")
if not matches:
    print("No matches on today's arg.1 scoreboard.")
    raise SystemExit

summary: esd.espn.ESPNMatchSummary = client.get_match_summary(
    matches[0].id, league="arg.1"
)
print(
    f"Match: {summary.home_team.name} {summary.home_team.score} - "
    f"{summary.away_team.score} {summary.away_team.name}"
)
print(f"Venue: {summary.venue_name}\n")

if summary.home_stats:
    print("Home Stats:")
    for stat in summary.home_stats[:8]:
        print(f"  {stat.label}: {stat.value}")

if summary.key_events:
    print("\nKey Events:")
    for ev in summary.key_events:
        print(f"  {ev.clock_display} [{ev.type_text}] {ev.text}")

"""Fetch a Promiedos match and print incidents grouped by match phase.

Makes network requests when executed.
"""

import esd

client = esd.PromiedosClient()

match = client.get_match("ediedag")

print(
    f"{match.home_team.short_name} {match.scores.home} - {match.scores.away} {match.away_team.short_name}"
)
print(f"{match.status.name} - {match.current_time}'")

print("First Half:")
for event in match.events.first_half:
    print(event)

print("Second Half:")
for event in match.events.second_half:
    print(event)

print("Extra Time:")
for event in match.events.extra_time:
    print(event)

print("Penalties:")
for event in match.events.penalties:
    print(event)

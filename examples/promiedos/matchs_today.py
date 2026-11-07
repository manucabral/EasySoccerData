"""Fetch today's Promiedos events and print scores, status and goals.

Makes network requests when executed.
"""

import esd

client = esd.PromiedosClient()
events = client.get_events()

for event in events:
    print(f"League name: {event.league.name} - {event.date}")
    for match in event.matches:
        print(
            f"{match.home_team.name} {match.scores.home} - {match.scores.away} {match.away_team.name}"
        )

        print(f"Status: {match.status.name} - {match.time_to_display}")
        goals = match.home_team.goals + match.away_team.goals
        if goals:
            for goal in goals:
                print(
                    f"Goal: {goal.full_name} ({goal.time_to_display}, is penalty: {goal.is_penalty})"
                )
        print("-----------------")
    print()

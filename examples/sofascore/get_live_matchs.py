"""Fetch the first live Sofascore match and print its clock, score and statistics.

Makes network requests when executed.
"""

import esd

client = esd.SofascoreClient()
events = client.get_events(live=True)
match = events[0]

print(f"Match ID: {match.id}, Status: {match.status.description}")
print(f"Time: {match.current_elapsed_minutes}' (total: {match.total_elapsed_minutes}')")
print(
    f"Board: {match.home_team.name} {match.home_score.current} - {match.away_score.current} {match.away_team.name}"
)

details = client.get_match_stats(match.id)
print(
    f"Possession: {details.all.match_overview.ball_possession.home_value}% - {details.all.match_overview.ball_possession.away_value}%"
)
print(
    f"Shots: {details.all.shots.shots_on_goal.home_value} - {details.all.shots.shots_on_goal.away_value}"
)

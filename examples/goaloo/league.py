"""Goaloo: league schedule + standings example."""
from esd.goaloo import GoalooClient

client = GoalooClient()

# 36 = English Premier League on Goaloo
league = client.get_league(36)
print(f"{league.name} {league.season}: {len(league.teams)} teams")

standings = client.get_standings(36)
print("\nStandings (top 5):")
for row in standings[:5]:
    print(f"  {row.rank}. {row.team.name:<22} PTS {row.points}")

matches = client.get_matches(36)
print(f"\nMatches: {len(matches)}")
for match in matches[:5]:
    print(
        f"  R{match.round} {match.home_team.name} "
        f"{match.home_score}-{match.away_score} {match.away_team.name}"
    )

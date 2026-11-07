"""Offline normalized analysis: nullable scores, ID joins and UTC dates. [pandas]."""

from datetime import datetime, timezone

import esd


def main():
    time = datetime(2024, 8, 16, 19, tzinfo=timezone.utc)
    dataset = esd.SoccerDataset(
        esd.DatasetMetadata(
            "espn",
            "example-league",
            2024,
            ("matches", "teams", "standings"),
            time,
            time,
            expected_tasks=("example",),
            successful_tasks=("example",),
        ),
        match_records=(
            esd.NormalizedMatch(
                "espn",
                match_id="played",
                kickoff=time,
                home_team_id="a",
                away_team_id="b",
                home_score=0,
                away_score=1,
            ),
            esd.NormalizedMatch(
                "espn", match_id="unknown-score", home_team_id="b", away_team_id="a"
            ),
        ),
        team_records=(
            esd.NormalizedTeam("espn", "a", "Home"),
            esd.NormalizedTeam("espn", "b", "Away"),
        ),
        standing_records=(
            esd.NormalizedStanding("espn", team_id="a", table_id="total", rank=2, points=0),
            esd.NormalizedStanding("espn", team_id="b", table_id="total", rank=1, points=3),
        ),
    )
    matches = dataset.matches
    # Missing is not zero. A recorded score alone does not establish final status.
    scored = matches.dropna(subset=["home_score", "away_score"]).copy()
    scored["total_goals"] = scored.home_score + scored.away_score
    assert len(scored) == 1 and scored.total_goals.iloc[0] == 1
    names = dataset.teams.rename(columns={"team_id": "home_team_id", "name": "home_name"})
    joined = matches.merge(
        names[["source", "home_team_id", "home_name"]],
        on=["source", "home_team_id"],
        how="left",
        validate="many_to_one",
    )
    print(
        joined[["match_id", "kickoff", "home_name", "home_score", "away_score"]].to_string(
            index=False
        )
    )
    print(
        dataset.standings.sort_values("rank")[
            ["table_id", "rank", "team_name", "points"]
        ].to_string(index=False)
    )
    print("Known-score matches:", len(scored), "unknown-score matches:", len(matches) - len(scored))


if __name__ == "__main__":
    main()

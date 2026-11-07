"""Analyze a saved 365Scores Champions League date range without network access.

Requires [pandas,parquet] or [full]. The team summary covers only saved matches.
"""

import argparse
import sys
from pathlib import Path

import esd

SUMMARY_COLUMNS = [
    "source", "team_id", "team_name", "played", "wins", "draws", "losses",
    "goals_for", "goals_against", "goal_difference",
]


def analyze(dataset):
    """Return fixtures, a team summary and mutually exclusive exclusion counts.

    365Scores status group 4 marks finished games. Results use the stored goals,
    without inferring shootout winners or qualification. Teams are grouped by
    source and native ID. Missing IDs are never replaced with names.
    """
    import pandas as pd

    if (
        dataset.metadata.source != "scores365" or dataset.metadata.league != "572"
        or "matches" not in dataset.metadata.tables
    ):
        raise ValueError("Choose a 365Scores Champions League matches snapshot")
    fixtures = dataset.matches.sort_values(["kickoff", "match_id"], na_position="last")
    finished = fixtures.source_status.eq("4").fillna(False)
    scores = (
        fixtures[["home_score", "away_score"]].notna().all(axis=1)
        & fixtures[["home_score", "away_score"]].ge(0).fillna(False).all(axis=1)
    )
    identities = (
        fixtures.home_team_id.notna() & fixtures.away_team_id.notna()
        & fixtures.home_team_id.ne("") & fixtures.away_team_id.ne("")
        & fixtures.home_team_id.ne(fixtures.away_team_id)
    ).fillna(False)
    excluded = {
        "not_finished": int((~finished).sum()),
        "missing_or_invalid_scores": int((finished & ~scores).sum()),
        "missing_or_invalid_team_ids": int((finished & scores & ~identities).sum()),
    }
    played = fixtures.loc[finished & scores & identities]
    appearances = []
    for side, opponent in (("home", "away"), ("away", "home")):
        team = played[["source", f"{side}_team_id", f"{side}_team_name",
                       f"{side}_score", f"{opponent}_score"]].rename(columns={
            f"{side}_team_id": "team_id", f"{side}_team_name": "team_name",
            f"{side}_score": "goals_for", f"{opponent}_score": "goals_against",
        })
        team["played"] = 1
        team["wins"] = team.goals_for.gt(team.goals_against).astype("Int64")
        team["draws"] = team.goals_for.eq(team.goals_against).astype("Int64")
        team["losses"] = team.goals_for.lt(team.goals_against).astype("Int64")
        appearances.append(team)
    appearances = pd.concat(appearances, ignore_index=True)
    metrics = ["played", "wins", "draws", "losses", "goals_for", "goals_against"]
    summary = appearances.groupby(["source", "team_id"], as_index=False)[metrics].sum()
    names = appearances[["source", "team_id", "team_name"]].drop_duplicates(
        ["source", "team_id"], keep="last",
    )
    summary = summary.merge(names, on=["source", "team_id"], validate="one_to_one")
    summary["goal_difference"] = summary.goals_for - summary.goals_against
    summary = summary[SUMMARY_COLUMNS].sort_values(["team_name", "team_id"], na_position="last")
    return fixtures, summary, excluded


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path, help="Saved Champions League snapshot directory")
    args = parser.parse_args(argv)
    try:
        dataset = esd.open_dataset(args.snapshot.expanduser())
        fixtures, summary, excluded = analyze(dataset)
    except ImportError as exc:
        parser.error(f'{exc} Install the analysis extras with python -m pip install -e ".[pandas,parquet]".')
    except (ValueError, OSError, esd.DatasetFormatError) as exc:
        parser.error(str(exc))
    print(f"UEFA Champions League | {dataset.metadata.start_date} to {dataset.metadata.end_date} (UTC)")
    print("Complete:", dataset.complete, "| Saved matches:", len(fixtures))
    print("Fixtures by UTC kickoff (unknown scores remain <NA>):")
    print(fixtures[[
        "match_id", "kickoff", "home_team_name", "home_score", "away_score", "away_team_name",
        "source_status", "source_status_text",
    ]].to_string(index=False))
    print("Team summary for this snapshot's date range. This is not the official standings.")
    if summary.empty:
        print("No finished matches with known scores and team IDs to summarize.")
    else:
        print(summary.to_string(index=False))
    print("Matches included in summary:", int(summary.played.sum()) // 2)
    for reason, count in excluded.items():
        print(f"Excluded ({reason}): {count}")
    for issue in dataset.errors:
        print(f"{issue.step} {issue.target}: {issue.error_type}: {issue.message}", file=sys.stderr)
    return 0 if dataset.complete else 1


if __name__ == "__main__":
    raise SystemExit(main())

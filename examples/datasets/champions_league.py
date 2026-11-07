"""Download up to seven UTC days of UEFA Champions League matches from 365Scores.

Uses the base installation. Running the script makes network requests and writes no files.
"""

import argparse
import sys
from datetime import datetime

import esd

CHAMPIONS_LEAGUE_ID = 572


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-date", default="2026-11-03", help="First UTC day, YYYY-MM-DD")
    parser.add_argument("--end-date", default="2026-11-04", help="Last UTC day, inclusive")
    parser.add_argument(
        "--season", type=int, default=2026, help="Caller year label; dates select matches"
    )
    args = parser.parse_args(argv)
    try:
        start = datetime.strptime(args.start_date, "%Y-%m-%d").date()
        end = datetime.strptime(args.end_date, "%Y-%m-%d").date()
        if start.isoformat() != args.start_date or end.isoformat() != args.end_date:
            raise ValueError("Dates must use YYYY-MM-DD")
        if not 0 <= (end - start).days <= 6:
            raise ValueError("Choose an ordered range of one to seven days")
        dataset = esd.load_dataset(
            source="scores365",
            league=CHAMPIONS_LEAGUE_ID,
            season=args.season,
            start_date=args.start_date,
            end_date=args.end_date,
            tables=["matches"],
            on_error="collect",
        )
    except ValueError as exc:
        parser.error(str(exc))

    print(f"UEFA Champions League | {args.start_date} to {args.end_date} (UTC)")
    print(
        f"Complete: {dataset.complete} | Matches: {len(dataset.match_records)} | Teams: {len(dataset.team_records)}"
    )
    for match in dataset.match_records:
        kickoff = match.kickoff.isoformat() if match.kickoff is not None else "Unknown"
        home = str(match.home_score) if match.home_score is not None else "?"
        away = str(match.away_score) if match.away_score is not None else "?"
        status = match.source_status_text or match.source_status or "Unknown"
        print(
            f"{match.match_id} | {kickoff} | {match.home_team_name} {home} - {away} {match.away_team_name} | {status}"
        )
    if dataset.complete and not dataset.match_records:
        print("No fixtures returned for this date range.")
    for issue in dataset.errors:
        print(f"{issue.step} {issue.target}: {issue.error_type}: {issue.message}", file=sys.stderr)
    return 0 if dataset.complete else 1


if __name__ == "__main__":
    raise SystemExit(main())

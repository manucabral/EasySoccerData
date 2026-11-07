"""Validate artificial records, partial coverage and duplicates offline. Base install."""

from dataclasses import replace
from datetime import datetime, timezone

import esd


def main():
    now = datetime(2026, 11, 7, tzinfo=timezone.utc)
    dataset = esd.SoccerDataset(
        esd.DatasetMetadata(
            "scores365", "572", 2026, ("matches", "teams"), now, now,
            coverage_scope="date_range", start_date="2026-11-03", end_date="2026-11-04",
            expected_tasks=("matches:2026-11-03",), successful_tasks=("matches:2026-11-03",),
        ),
        match_records=(esd.NormalizedMatch(
            "scores365", match_id="sample-1", competition_id="572", kickoff=now.replace(day=3),
            home_team_id="home", away_team_id="away", home_score=0, away_score=None,
        ),),
        team_records=(esd.NormalizedTeam("scores365", "home"), esd.NormalizedTeam("scores365", "away")),
    )
    clean = esd.validate_dataset(dataset)
    assert clean.valid and not clean.issues
    partial = replace(
        dataset, metadata=replace(dataset.metadata, successful_tasks=()),
        errors=(esd.DatasetIssue("matches", "2026-11-03", "SourceError", "Sample failed day"),),
    )
    report = esd.validate_dataset(partial)
    assert report.valid and report.warnings
    print("Partial dataset:", report.valid, "| Warnings:", len(report.warnings))
    invalid_match = replace(dataset.match_records[0], home_score=-1, away_team_id="not-in-table")
    invalid = replace(dataset, match_records=(invalid_match, invalid_match))
    report = esd.validate_dataset(invalid)
    assert not report.valid
    assert {issue.code for issue in report.errors} == {"negative_score", "duplicate_key"}
    for issue in report.issues:
        print(issue.severity, issue.code, issue.table, issue.row_index, issue.field, issue.message)
    assert dataset.match_records[0].home_score == 0
    assert dataset.match_records[0].away_score is None


if __name__ == "__main__":
    main()

"""Artificial field counts and partial tasks, without HTTP or optional packages."""

import argparse
import json
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from time import sleep

import esd


@contextmanager
def workflow_directory():
    temporary = TemporaryDirectory(prefix="esd-field-coverage-")
    try:
        yield Path(temporary.name)
    finally:
        for attempt in range(3):
            try:
                temporary.cleanup()
            except OSError as exc:
                if getattr(exc, "winerror", None) != 145 or attempt == 2:
                    raise
                sleep(0.05 * (attempt + 1))
            else:
                break


def fixture():
    """Invented player rows and one failed requested match, not a real fixture."""
    now = datetime(2026, 11, 8, tzinfo=timezone.utc)
    return esd.SoccerDataset(
        esd.DatasetMetadata("espn", "example.cup", 2026, ("lineups", "player_match_stats"), now, now,
                            coverage_scope="match_ids", requested_match_ids=("1", "2"),
                            expected_tasks=("match_details:1", "match_details:2"), successful_tasks=("match_details:1",),
                            response_fetched_at=(("match_details:1", now.isoformat()),), cached_tasks=("match_details:1",)),
        lineup_records=(esd.NormalizedLineup("espn", "1", "10", "101", starter=False),
                        esd.NormalizedLineup("espn", "1", "10", "102", starter=None)),
        player_match_stat_records=(esd.NormalizedPlayerMatchStats("espn", "1", "10", "101", goals=0),
                                   esd.NormalizedPlayerMatchStats("espn", "1", "10", "102", goals=None)),
        errors=(esd.DatasetIssue("match_details", "2", "SourceBlocked", "Artificial unavailable match"),),
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pandas", action="store_true")
    parser.add_argument("--parquet", action="store_true")
    args = parser.parse_args(argv)
    data = fixture()
    report = esd.inspect_dataset_coverage(data)
    goals = next(row for row in report.fields if row.table == "player_match_stats" and row.field == "goals")
    starter = next(row for row in report.fields if row.table == "lineups" and row.field == "starter")
    assert goals.present_count == goals.missing_count == goals.zero_count == 1
    assert starter.false_count == 1 and starter.zero_count is None
    assert not report.complete and all(table.task_status == "partial" for table in report.tables)
    assert report.tasks[0].cached and report.tasks[0].fetched_at == data.metadata.started_at
    assert esd.get_dataset_field_capabilities("espn", "player_match_stats")["minutes"].support == "unavailable"
    assert esd.get_dataset_field_capabilities("sofascore", "player_match_stats")["minutes"].support == "mapped"
    assert json.loads(json.dumps(report.to_dict()))["format"] == "easysoccerdata-coverage"
    print("Artificial coverage: goals present=1, missing=1, numeric zeros=1; starter False=1")
    print("Both player tables have partial tasks; the failed requested match contributes no rows")
    print("ESPN minutes: unavailable in this adapter; Sofascore minutes: mapped, subject to response availability")
    if args.parquet:
        with workflow_directory() as directory:
            path = data.save(directory / "source")
            restored = esd.open_dataset(path)
            assert esd.inspect_dataset_coverage(restored) == report
            print("Snapshot reproduces counts, errors and original cache dates without HTTP or pandas")
    if args.pandas:
        frame = report.to_dataframe()
        assert str(frame.zero_count.dtype) == "Int64" and str(frame.present_ratio.dtype) == "Float64"
        print(frame.loc[frame.field.isin(["goals", "minutes", "starter"]),
                        ["table", "field", "support", "present_count", "missing_count", "zero_count", "false_count"]])


if __name__ == "__main__":
    main()

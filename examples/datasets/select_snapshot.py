"""Read selected snapshot tables and native match IDs without source requests.

Requires [parquet]. Use --demo for a temporary, invented two-match snapshot.
"""

import argparse
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from esd import DatasetFormatError, DatasetMetadata, NormalizedMatch, SoccerDataset, open_dataset


def show(path, tables, match_ids):
    dataset = open_dataset(path, tables=tables, match_ids=match_ids)
    print("Tables:", dataset.metadata.tables)
    print("Original tables:", dataset.metadata.original_tables)
    print("Local match IDs:", dataset.metadata.snapshot_match_ids)
    print("Loaded matches:", tuple(row.match_id for row in dataset.match_records))
    print("Original download complete:", dataset.complete)
    print("Original failures:", len(dataset.errors))
    return dataset


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--open-dir", type=Path)
    mode.add_argument("--demo", action="store_true")
    parser.add_argument("--table", action="append")
    parser.add_argument("--match-id", action="append")
    args = parser.parse_args(argv)
    try:
        if args.demo:
            timestamp = datetime(2024, 1, 1, tzinfo=timezone.utc)
            dataset = SoccerDataset(
                DatasetMetadata("espn", "example", 2024, ("matches",), timestamp,
                                timestamp, calendar_loaded=True),
                match_records=(NormalizedMatch("espn", "001", kickoff=timestamp),
                               NormalizedMatch("espn", "002")),
            )
            with TemporaryDirectory(prefix="esd-selection-") as directory:
                selected = show(dataset.save(Path(directory) / "snapshot"),
                                args.table or ("matches",), args.match_id or ("001",))
                assert selected.match_records == tuple(
                    row for row in dataset.match_records
                    if row.match_id in (args.match_id or ("001",))
                )
        else:
            show(args.open_dir.expanduser(), args.table, args.match_id)
    except (OSError, ValueError, ImportError, DatasetFormatError) as exc:
        parser.exit(2, f"{exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

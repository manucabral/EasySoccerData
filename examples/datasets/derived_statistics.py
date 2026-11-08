"""Calculate row-level statistics from invented data or a local snapshot.

The demo requires only the base installation. --open-dir needs [parquet].
--pandas independently requires [pandas]. No source requests are made.
"""

import argparse
import json
from pathlib import Path

from esd import (
    DatasetFormatError,
    NormalizedPlayerMatchStats,
    derive_statistics,
    derived_statistics_to_dataframe,
    open_dataset,
)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--open-dir", type=Path)
    parser.add_argument("--table", choices=("player_match_stats", "player_stats", "match_stats"),
                        default="player_match_stats")
    parser.add_argument("--match-id", action="append")
    display = parser.add_mutually_exclusive_group()
    display.add_argument("--pandas", action="store_true")
    display.add_argument("--json", action="store_true", help="Print JSON instead of the text summary")
    args = parser.parse_args(argv)
    if args.open_dir is None and (args.match_id or args.table != "player_match_stats"):
        parser.error("--match-id and other tables require --open-dir")
    if args.match_id and args.table == "player_stats":
        parser.error("Season statistics cannot be filtered by match ID")
    try:
        dataset = None
        if args.open_dir is None:
            records = (
                NormalizedPlayerMatchStats("scores365", "demo", "10", "001", minutes=45,
                                           goals=1, shots=4, shots_on_target=2, passes=20,
                                           accurate_passes=15, xg=0.75),
                NormalizedPlayerMatchStats("espn", "demo", "20", "002", goals=0, shots=0),
            )
        else:
            dataset = open_dataset(args.open_dir.expanduser(), tables=(args.table,), match_ids=args.match_id)
            attribute = {"player_match_stats": "player_match_stat_records",
                         "player_stats": "player_stat_records", "match_stats": "match_stat_records"}[args.table]
            records = getattr(dataset, attribute)
        results = tuple(derive_statistics(record) for record in records)
        if args.json:
            print(json.dumps([result.to_dict() for result in results], indent=2, allow_nan=False))
        elif args.pandas:
            print(derived_statistics_to_dataframe(results).to_string(index=False))
        else:
            if dataset is None:
                print("Invented demo observations")
            else:
                print("Original download complete:", dataset.complete, "| Failures:", len(dataset.errors))
            for result in results:
                print("Source:", result.record.source, "| Player:", getattr(result.record, "player_id", None),
                      "| Match:", getattr(result.record, "match_id", None))
                for metric in result.metrics:
                    print(metric.name, "=", metric.value, "|", metric.status, "|",
                          metric.numerator_field, "/", metric.denominator_field, "*", metric.scale)
    except (OSError, ValueError, ImportError, DatasetFormatError) as exc:
        parser.exit(2, f"{exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Inspect adapter fields or coverage in a saved snapshot, without source requests.

--source uses the base installation. --open-dir requires [parquet]. Only the
optional --pandas display requires [pandas]. Existing report files are preserved.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

import esd


def write_report(path, document):
    """Publish complete JSON to a new caller-selected file."""
    path = path.expanduser().absolute()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with NamedTemporaryFile("w", prefix=".esd-coverage-", suffix=".json", dir=path.parent,
                                encoding="utf-8", delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(document, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
        os.link(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink()
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--source", choices=tuple(esd.get_dataset_capabilities()))
    mode.add_argument("--open-dir", type=Path)
    parser.add_argument("--table", action="append", help="Normalized table; repeat to select more")
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--pandas", action="store_true")
    args = parser.parse_args(argv)
    if args.source is not None and args.pandas:
        parser.error("--pandas displays snapshot coverage; choose --open-dir")
    try:
        if args.output_json is not None and (args.output_json.expanduser().exists() or args.output_json.expanduser().is_symlink()):
            raise FileExistsError(f"Report destination already exists: {args.output_json}")
        if args.source is not None:
            tables = args.table or esd.get_dataset_capabilities(args.source).tables
            rows = [capability for table in dict.fromkeys(tables)
                    for capability in esd.get_dataset_field_capabilities(args.source, table).values()]
            for row in rows:
                print(row.table, row.field, "|", row.support, "|", row.dtype,
                      "| Unit:", row.unit, "| Model:", row.model, "| Coordinates:", row.coordinate_system)
            from dataclasses import asdict

            document = {"format": "easysoccerdata-field-contracts", "format_version": 1,
                        "source": args.source, "fields": [asdict(row) for row in rows]}
            complete = True
        else:
            dataset = esd.open_dataset(args.open_dir.expanduser())
            report = esd.inspect_dataset_coverage(dataset, tables=args.table)
            print("Source:", report.metadata.source, "| League:", report.metadata.league,
                  "| Season label:", report.metadata.season, "| Complete tasks:", report.complete)
            for table in report.tables:
                print(table.table, "| Rows:", table.row_count, "| Tasks:", table.task_status, table.task_keys)
            for row in report.fields:
                print(row.table, row.field, "| Contract:", row.capability.support,
                      "| Present/missing:", row.present_count, row.missing_count,
                      "| Zeros:", row.zero_count, "| False:", row.false_count, "| Blank:", row.blank_count)
            for task in report.tasks:
                print("Task:", task.key, task.status, "| Cached:", task.cached, "| Original fetch:", task.fetched_at)
            for error in report.errors:
                print(f"{error.step} {error.target}: {error.error_type}: {error.message}", file=sys.stderr)
            if args.pandas:
                print(report.to_dataframe())
            document, complete = report.to_dict(), report.complete
        print("Column support and non-null counts do not establish complete league or raw-source coverage")
        if args.output_json is not None:
            print("Saved report:", write_report(args.output_json, document))
        return 0 if complete else 1
    except (ValueError, OSError, ImportError) as exc:
        parser.error(str(exc))
    except esd.ESDException as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

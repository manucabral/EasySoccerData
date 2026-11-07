"""Run one provider query: --source goaloo --source-timezone Asia/Shanghai.

Use --list to inspect all nine contracts without network access. Choose a
timezone from the source's verified date convention; naive dates require it.
"""

import argparse
from zoneinfo import ZoneInfoNotFoundError

import esd

QUERIES = {
    "espn": {"league": "eng.1", "season": 2024, "tables": ["matches", "standings"]},
    "sofascore": {"league": 17, "season": 2024, "season_id": 61627},
    "scores365": {
        "league": 7,
        "season": 2024,
        "start_date": "2024-08-16",
        "end_date": "2024-08-16",
    },
    "understat": {
        "league": "EPL",
        "season": 2024,
        "tables": ["matches", "match_stats", "player_stats", "shots"],
        "match_ids": [26602],
    },
    "fbref": {
        "league": 9,
        "season": 2024,
        "start_date": "2024-08-16",
        "end_date": "2024-08-16",
        "tables": ["matches", "match_stats"],
    },
    "goaloo": {
        "league": 36,
        "season": 2024,
        "source_season": "2024-2025",
        "tables": ["matches", "standings"],
    },
    "promiedos": {
        "league": "hc",
        "season": 2026,
        "start_date": "2026-11-06",
        "end_date": "2026-11-06",
    },
    "besoccer": {
        "league": "torneo_final",
        "season": 2026,
        "start_date": "2026-11-06",
        "end_date": "2026-11-06",
    },
    "transfermarkt": {
        "league": "GB1",
        "season": 2026,
        "tables": ["teams", "players", "market_values", "transfers"],
        "club_ids": [281],
        "player_ids": [418560],
    },
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--source", choices=tuple(QUERIES), default="espn")
    parser.add_argument("--source-timezone")
    parser.add_argument("--cache-dir")
    parser.add_argument("--league", help="Native competition code, ID or slug")
    parser.add_argument("--season", type=int, help="Four-digit year label")
    parser.add_argument("--season-id", type=int, help="Native Sofascore/365Scores season ID")
    parser.add_argument("--source-season", help="Native Goaloo season, e.g. 2024-2025")
    parser.add_argument("--start-date", help="YYYY-MM-DD")
    parser.add_argument("--end-date", help="YYYY-MM-DD")
    parser.add_argument("--tables", nargs="+", help="Tables to request; see --list")
    parser.add_argument("--match-ids", nargs="+", type=int, help="Understat shot selection")
    parser.add_argument("--club-ids", nargs="+", type=int, help="Transfermarkt club selection")
    parser.add_argument("--player-ids", nargs="+", type=int, help="Transfermarkt player selection")
    parser.add_argument("--max-pages", type=int, help="Sofascore pages per direction")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--on-error", choices=("collect", "raise"), default="collect")
    parser.add_argument("--preview", type=int, default=0, help="Print up to N records per table")
    parser.add_argument("--output", help="New Parquet snapshot directory; requires [parquet]")
    args = parser.parse_args()
    if args.list:
        for source, contract in esd.get_dataset_capabilities().items():
            print(source, contract.selection, contract.tables)
        return 0
    if args.preview < 0:
        parser.error("--preview must be nonnegative")
    query = dict(QUERIES[args.source])
    for name in (
        "league",
        "season",
        "season_id",
        "source_season",
        "source_timezone",
        "start_date",
        "end_date",
        "tables",
        "match_ids",
        "club_ids",
        "player_ids",
        "max_pages",
    ):
        if getattr(args, name) is not None:
            query[name] = getattr(args, name)
    tables = query.get("tables", ["matches"])
    # Discard sample-only selections when the caller chooses different tables.
    if args.source == "besoccer" and "matches" not in tables:
        for name in ("start_date", "end_date"):
            if getattr(args, name) is None:
                query.pop(name, None)
    if args.source == "understat" and "shots" not in tables and args.match_ids is None:
        query.pop("match_ids", None)
    if args.source == "transfermarkt":
        if "teams" not in tables and args.club_ids is None:
            query.pop("club_ids", None)
        if not set(tables) & {"players", "market_values", "transfers"} and args.player_ids is None:
            query.pop("player_ids", None)
    try:
        dataset = esd.load_dataset(
            source=args.source,
            **query,
            cache_dir=args.cache_dir,
            refresh=args.refresh,
            on_error=args.on_error,
            progress=lambda task: print(task.step, task.target, task.success, task.cached),
        )
    except esd.DatasetLoadError as exc:
        dataset = exc.dataset
    except (ValueError, ZoneInfoNotFoundError) as exc:
        parser.error(str(exc))
    print("Complete:", dataset.complete, "Scope:", dataset.metadata.coverage_scope)
    for issue in dataset.errors:
        print(issue.step, issue.target, issue.error_type, issue.message)
    print("Matches:", len(dataset.match_records), "Teams:", len(dataset.team_records))
    print(
        "Players:",
        len(dataset.player_records),
        "Valuations:",
        len(dataset.market_value_records),
        "Transfers:",
        len(dataset.transfer_records),
    )
    attributes = {
        "matches": "match_records",
        "teams": "team_records",
        "standings": "standing_records",
        "match_stats": "match_stat_records",
        "player_stats": "player_stat_records",
        "shots": "shot_records",
        "players": "player_records",
        "market_values": "market_value_records",
        "transfers": "transfer_records",
    }
    if args.preview:
        for table in dataset.metadata.tables:
            print(table, getattr(dataset, attributes[table])[: args.preview])
    if args.output:
        try:
            print("Snapshot:", dataset.save(args.output))
        except (ImportError, OSError, ValueError) as exc:
            parser.error(str(exc))
    return 0 if dataset.complete else 1


if __name__ == "__main__":
    raise SystemExit(main())

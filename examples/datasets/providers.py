"""Run one provider query: --source goaloo --source-timezone Asia/Shanghai.

Use --list to inspect all nine contracts without network access. Choose a
timezone from the source's verified date convention; naive dates require it.
"""

import argparse

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
    args = parser.parse_args()
    if args.list:
        for source, contract in esd.get_dataset_capabilities().items():
            print(source, contract.selection, contract.tables)
        return
    query = dict(QUERIES[args.source])
    if args.source_timezone is not None:
        query["source_timezone"] = args.source_timezone
    dataset = esd.load_dataset(
        source=args.source,
        **query,
        cache_dir=args.cache_dir,
        on_error="collect",
        progress=lambda task: print(task.step, task.target, task.success, task.cached),
    )
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
    # Optional: dataset.matches (pandas), dataset.save(your_path) (parquet).


if __name__ == "__main__":
    main()

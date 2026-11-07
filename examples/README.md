# Examples

Dataset examples target the unreleased 0.2.0 checkout. From the repository root:

```sh
python -m pip install -e .
python examples/datasets/providers.py --list
```

Add `".[pandas]"` for DataFrames, `".[parquet]"` for snapshots or `".[full]"`
for both. The base library and identity-linking helpers require neither extra.

## Offline examples

These scripts use artificial records or mocked source responses. They do not
contact a provider or launch a browser. Temporary-file examples clean up after
themselves.

| Script | Extra | What it demonstrates |
| :--- | :--- | :--- |
| [Provider contracts](datasets/providers.py) with `--list` | Base | All nine sources and supported tables |
| [Partial results](datasets/partial_results.py) | Base | `raise`, `collect`, attached records and failed days |
| [Cache reuse](datasets/cache_resume_offline.py) | Base | First download, disk reuse, original timestamps and forced refresh |
| [Match linkage](datasets/link_matches.py) | Base | Explicit competition/team mappings and ambiguous candidates |
| [Native models to DataFrames](pandas/matches_and_standings.py) | pandas | Flattening, nullable scores and ID joins |
| [Common provider tables](pandas/normalized_tables.py) | pandas | ESPN/365Scores columns and source-local identifiers |
| [Dataset analysis](pandas/dataset_analysis.py) | pandas | Unknown scores, UTC dates and validated team joins |
| [Snapshot round trip](datasets/parquet_roundtrip.py) | parquet | Save/open without pandas or network access |

Run the applicable set with network and browser calls blocked:

```sh
python scripts/check_examples.py --extra base
python scripts/check_examples.py --extra full
```

Install the matching extras before choosing `pandas`, `parquet` or `full`.

## Live dataset queries

`datasets/providers.py` runs one query. `--list` and `--help` work offline;
otherwise it makes network requests. Sample IDs/dates are starting points,
not a guarantee of historical availability. Override them for your selection.

```sh
python examples/datasets/providers.py --source espn --league eng.1 --season 2024 --preview 2
python examples/datasets/providers.py --source scores365 --league 7 --season 2024 --start-date 2024-08-16 --end-date 2024-08-18
python examples/datasets/providers.py --source sofascore --league 17 --season 2024 --season-id 61627 --max-pages 100
python examples/datasets/providers.py --source understat --tables player_stats --preview 2
python examples/datasets/providers.py --source fbref --tables match_stats --source-timezone UTC
python examples/datasets/providers.py --source goaloo --source-season 2024-2025 --source-timezone Asia/Shanghai
python examples/datasets/providers.py --source promiedos --league hc --start-date 2026-11-06 --end-date 2026-11-06 --source-timezone America/Argentina/Buenos_Aires
python examples/datasets/providers.py --source besoccer --tables standings
python examples/datasets/providers.py --source transfermarkt --tables players market_values transfers --player-ids 418560
```

Timezone examples assume that you have checked the source's timestamp convention.
Do not use UTC to silence a timezone error if the source uses another zone.
IANA names require system timezone data or `python -m pip install tzdata`.

`--cache-dir C:/data/esd/responses` selects persistent response storage.
`--refresh` bypasses cached responses. `--output C:/data/esd/snapshot-1` writes
a new Parquet snapshot and needs the parquet extra; the destination must not exist.
On Linux/macOS use paths such as `/home/me/data/esd/responses` instead.
Snapshots can preserve partial results, so always inspect `complete` and errors.

The runner exits with `0` when all requested tasks succeed, `1` for a partial
download and `2` for invalid arguments or a failed requested snapshot write.
`--on-error raise` stops at the first failed task and reports its partial dataset;
the default `collect` continues. No files are written without an explicit cache
or output path.

## Individual clients

These folders contain source-specific examples. They make network requests when
executed, and many run their query immediately. Live responses and available
fields vary. Source blocks or maintenance can prevent a script from fetching data.

| Provider | Examples |
| :--- | :--- |
| Sofascore | [Matches, standings, players, lineups and shots](sofascore/) |
| FBref | [Schedules, match reports and player statistics](fbref/) |
| Promiedos | [Matches, tournaments, events and lineups](promiedos/) |
| Goaloo | [League metadata and standings](goaloo/league.py) |
| 365Scores | [Matches, details, standings and search](scores365/) |
| Understat | [Matches, player metrics and shots](understat/) |
| Transfermarkt | [Profiles, valuations and transfers](transfermarkt/) |
| ESPN | [Scoreboards, summaries and standings](espn/) |
| BeSoccer | [Matches and standings](besoccer/) |

For configurable providers, scope, error handling and matching rules, read the
[dataset cookbook](../guides/datasets.md).

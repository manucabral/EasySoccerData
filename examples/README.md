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

| Script | Extra | Behavior shown |
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

### Champions League: a short date range

[champions_league.py](datasets/champions_league.py) downloads matches for two UTC
days using the base installation. It prints IDs, kickoff times, teams, scores and
source statuses. It does not require pandas or PyArrow and writes no files.

```sh
python examples/datasets/champions_league.py
python examples/datasets/champions_league.py --start-date 2026-11-03 --end-date 2026-11-04 --season 2026
```

The default dates are November 3-4, 2026. Both bounds are inclusive, with a maximum
of seven days per call. The competition ID is `572` for the Champions League;
`332` is a separate qualifying competition. `--season` labels the records; the
date range selects the matches. Kickoff times use UTC; status codes come from 365Scores.
An unknown score is printed as `?`, and zero stays zero.

If a day fails, the script displays the successful days and reports the failed
tasks on stderr, with exit code `1`. A complete request returns `0`, including
an empty selection. Invalid arguments return `2`. `--help` works offline.

### Other provider queries

`datasets/providers.py` runs one query. `--list` and `--help` work offline;
otherwise it makes network requests. Use the selection flags to replace the
sample IDs and dates. A provider may no longer serve the sample dates.

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

Set `--source-timezone` to the zone used by the source's naive timestamps.
The UTC and Asia/Shanghai values above illustrate the flag syntax.
IANA names require system timezone data or `python -m pip install tzdata`.

`--cache-dir C:/data/esd/responses` selects persistent response storage.
`--refresh` bypasses cached responses. `--output C:/data/esd/snapshot-1` writes
a new Parquet snapshot and needs the parquet extra; the destination must not exist.
On Linux/macOS use paths such as `/home/me/data/esd/responses` instead.
Check `complete` and `errors` before using a saved dataset; snapshots can contain
partial results.

The runner exits with `0` when all requested tasks succeed, `1` for a partial
download and `2` for invalid arguments or a failed requested snapshot write.
`--on-error raise` stops at the first failed task and reports its partial dataset;
the default `collect` continues. No files are written without an explicit cache
or output path.

## Individual clients

These folders contain source-specific examples. Importing a script makes no
requests. Running it directly calls `main()` and queries the provider. Source
blocks are reported with exit code `1`. Sofascore and FBref examples close their
clients on success, early return and source errors.

Live responses and available fields vary. Source blocks or maintenance can
prevent a script from fetching data.

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
[dataset guide](../guides/datasets.md).

## Live provider checks

Run small dataset queries for the nine providers separately from the offline tests:

```sh
python scripts/check_sources.py --output ./my-data/live-checks.json
python scripts/check_sources.py --source espn promiedos --date 2026-11-07
```

The default checks select one day, standings table, season response or club.
They do not traverse fixture calendars or fetch individual shot lists. Each provider
runs in its own process, with a default limit of 45 seconds and three HTTP attempts.
`--timeout` and `--max-requests` change those limits. No browser is launched.

The report includes the selection, UTC check times, HTTP statuses, row counts
and source errors. Records are checked for their model, source ID and UTC kickoff
when present. `ok` means the selected query returned records. `empty` means it
succeeded without records. Blocks, missing resources, source errors and timeouts
have separate statuses. Exit code `1` means at least one query did not complete.
A successful sample does not establish that every method or historical date works.

The dated FBref sample uses `Europe/London`; Promiedos uses
`America/Argentina/Buenos_Aires`. These are the timezone assumptions of these
queries. On systems without IANA timezone data, install `tzdata` before running
them. pandas and PyArrow are not required. A JSON file is written only with
`--output`. The checks do not run as part of ordinary CI.

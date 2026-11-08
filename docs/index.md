# EasySoccerData

`EasySoccerData` (`esd`) queries football fixtures, live scores, standings, player statistics and normalized multi-provider datasets across nine football data sources.

- Provider clients (`esd.SofascoreClient`, `esd.ESPNClient`, `esd.UnderstatClient` and six others) return each source's native dataclass models.
- Dataset functions (`esd.load_dataset`, `esd.open_dataset`, `esd.get_catalog`) download normalized tables (`SCHEMA_VERSION == "6"`), cache HTTP responses locally, write Parquet snapshots, compute per-90 derived rates and compare linked fixtures across providers.

## Installation

```sh
pip install EasySoccerData
```

| Command | Added packages | Purpose |
| :--- | :--- | :--- |
| `pip install EasySoccerData` | `httpx`, `lxml`, `curl-cffi`, `playwright` | Provider clients, normalized record tuples, response cache, catalog, validation and comparisons |
| `pip install "EasySoccerData[pandas]"` | `pandas>=2.0` | DataFrame properties (`.matches`, `.standings`, `.player_match_stats`) and `esd.to_dataframe()` |
| `pip install "EasySoccerData[parquet]"` | `pyarrow>=17.0` | `dataset.save(...)` and `esd.open_dataset(...)` local Parquet snapshots |
| `pip install "EasySoccerData[full]"` | `pandas>=2.0`, `pyarrow>=17.0` | All optional runtime dependencies |

When `use_playwright=True` is enabled on `SofascoreClient` or `FBrefClient`, Playwright launches the system's installed Google Chrome (`channel="chrome"`) or a custom executable via `chrome_path=...` instead of downloading a separate Playwright Chromium binary.

## First queries

```py
import esd

# Provider client query
espn = esd.ESPNClient()
for match in espn.get_scoreboard(league="eng.1", date="20250406"):
    print(f"{match.home_team.name} {match.home_team.score} - {match.away_team.score} {match.away_team.name}")

# Normalized dataset download, validation and Parquet snapshot
dataset = esd.load_dataset(
    source="espn",
    league="uefa.champions",
    season=2024,
    tables=("matches", "teams", "standings"),
    cache_dir="./cache",
)
assert esd.validate_dataset(dataset).valid
dataset.save("./snapshots/ucl-2024")
```

## Documentation sections

- [Quickstart](quickstart.md): client queries, DataFrame export, concurrent requests and normalized datasets.
- [Datasets, cache and snapshots](guides/datasets.md): `load_dataset`, `ResponseCache`, `dataset.save` and selective `open_dataset`.
- [Discovery and catalog](guides/discovery-and-catalog.md): `list_competitions`, `list_seasons` and `get_catalog`.
- [Match detail tables](guides/detail-tables.md): `match_stats`, `lineups`, `player_match_stats`, `match_events` and `shots` by native match ID.
- [Validation, coverage and metrics](guides/coverage-and-metrics.md): `validate_dataset`, `inspect_dataset_coverage` and `derive_statistics`.
- [Cross-provider comparisons](guides/comparisons.md): `IdentityMap`, `link_dataset_matches`, `compare_match_statistics`, `compare_match_events` and `compare_match_players`.
- [Providers and limits](providers.md): selection contracts, supported tables and source constraints across all nine providers.
- [API reference](reference/clients.md): signatures, parameter tables, return types and raised exceptions.

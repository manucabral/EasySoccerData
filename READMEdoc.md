<h1 align="center">EasySoccerData</h1>

<p align="center">
<img alt="PyPI - Version" src="https://img.shields.io/pypi/v/EasySoccerData?color=00329e">
<img alt="Pepy Total Downloads" src="https://img.shields.io/pepy/dt/EasySoccerData?color=009903">
<img alt="GitHub License" src="https://img.shields.io/github/license/manucabral/easysoccerdata">
<img alt="GitHub Actions Workflow Status" src="https://img.shields.io/github/actions/workflow/status/manucabral/easysoccerdata/pylint.yml">
</p>

<p align="center">
A Python library for football fixtures, live scores, standings and player statistics from nine providers.
</p>

# Installation

```sh
pip install EasySoccerData
```

| Command | Added packages | Purpose |
| :--- | :--- | :--- |
| `pip install EasySoccerData` | `httpx`, `lxml`, `curl-cffi`, `playwright` | Provider clients, normalized record tuples, response cache, catalog, validation and comparisons |
| `pip install "EasySoccerData[pandas]"` | `pandas>=2.0` | DataFrame properties (`.matches`, `.standings`, `.player_match_stats`) and `esd.to_dataframe()` |
| `pip install "EasySoccerData[parquet]"` | `pyarrow>=17.0` | `dataset.save(...)` and `esd.open_dataset(...)` |
| `pip install "EasySoccerData[full]"` | `pandas>=2.0`, `pyarrow>=17.0` | All optional runtime dependencies |

When `use_playwright=True` is passed to `SofascoreClient` or `FBrefClient`, Playwright uses the system's installed Google Chrome (`channel="chrome"`) or `chrome_path=...` without downloading a separate Chromium build.

# Quickstart

```py
import esd

# Provider client query
espn = esd.ESPNClient()
matches = espn.get_scoreboard(league="eng.1", date="20250406")

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

See the [published documentation](https://manucabral.github.io/EasySoccerData/), [`guides/datasets.md`](guides/datasets.md) and [`examples/README.md`](examples/README.md).

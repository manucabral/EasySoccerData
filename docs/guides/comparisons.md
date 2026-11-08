# Cross-provider comparisons

`EasySoccerData` links matches across providers using reviewed competition and club identities (`IdentityMap`) and compares team statistics (`compare_match_statistics`), match events (`compare_match_events`) and lineups/player statistics (`compare_match_players`).

## Build an `IdentityMap`

Start from `esd.get_catalog().identities()` for competition and club references, and extend it with `EntityAlias("player", ...)` entries when comparing events or lineups across providers:

```py
import esd

catalog = esd.get_catalog()
identities = catalog.identities().with_aliases([
    esd.EntityAlias("player", "ucl-p1", "espn", "301234", team_id="359"),
    esd.EntityAlias("player", "ucl-p1", "sofascore", "901234", team_id="42"),
    esd.EntityAlias("player", "ucl-p1", "scores365", "1101", team_id="134"),
])
```

> On `scores365`, `lineups`, `player_match_stats` and `match_events` use the game-level `member["id"]` as `player_id` (while storing `athleteId` in `source_athlete_id`). Map the normalized `player_id` in `EntityAlias("player", ..., "scores365", member_id)`.

## Check compatibility and link matches

`check_dataset_compatibility` verifies schema versions, shared tables and mapped competition/team identities. `link_dataset_matches` pairs fixtures one-to-one using mapped competition, home/away teams and UTC kickoff time within `tolerance_seconds` (default `300`):

```py
import esd

compat = esd.check_dataset_compatibility(espn_ds, sofascore_ds, identities=identities)
print("Can match:", compat.can_match, "Shared tables:", compat.shared_tables)

linkage = esd.link_dataset_matches(espn_ds, sofascore_ds, identities=identities, tolerance_seconds=300)
for link in linkage.links:
    print(link.left_match_id, "<->", link.right_match_id, f"diff={link.kickoff_difference_seconds}s")
```

## Compare team match statistics

`esd.compare_match_statistics` compares numeric team totals across linked matches and supports per-metric tolerances:

```py
import esd

stats_report = esd.compare_match_statistics(
    espn_ds,
    sofascore_ds,
    identities=identities,
    metrics=("home_shots", "away_shots", "home_possession_pct", "home_xg"),
    tolerances={"home_possession_pct": 1.0},
)
df = stats_report.to_dataframe()
print(df[["metric", "left_value", "right_value", "delta", "status"]])
```

Cross-source `xg` and win/draw/loss forecast fields are reported with `status="source_specific"` because each provider uses its own model.

## Compare match events

`esd.compare_match_events` pairs goals, cards and substitutions using mapped player/team identities, shootout flags, periods and `minute_tolerance` (default `1`). Because `sofascore` incidents leave `source_period` as `None`, pass `allow_unknown_period=True` when comparing against `sofascore`:

```py
import esd

events_report = esd.compare_match_events(
    espn_ds,
    sofascore_ds,
    identities=identities,
    minute_tolerance=1,
    allow_unknown_period=True,
)
for row in events_report.comparisons:
    print(row.event_family, row.status, row.left_minute, row.right_minute, row.different_fields)
```

## Compare lineups and player statistics

`esd.compare_match_players` pairs players within linked fixtures using explicit player aliases and compares both lineup attributes (`starter`, `jersey_number`, `position`) and `player_match_stats` metrics:

```py
import esd

players_report = esd.compare_match_players(
    espn_ds,
    sofascore_ds,
    identities=identities,
    metrics=("minutes", "goals", "assists", "shots", "passes"),
    position_aliases={("espn", "F"): "FW", ("sofascore", "F"): "FW"},
)
lineups_df = players_report.lineups_to_dataframe()
stats_df = players_report.statistics_to_dataframe()
```

## Champions League workflow

[`examples/datasets/champions_workflow.py`](https://github.com/manucabral/EasySoccerData/blob/main/examples/datasets/champions_workflow.py) runs season discovery, download, validation, coverage inspection, Parquet snapshot save, selective `open_dataset`, per-90 derived statistics and three-way comparisons across ESPN, Sofascore and 365Scores:

```sh
# Run offline using bundled synthetic fixtures
python examples/datasets/champions_workflow.py

# Run against live provider endpoints with a response cache
python examples/datasets/champions_workflow.py --live --cache-dir ./cache/champions \
  --espn-match-id 704910 --sofascore-match-id 12173507 --scores365-match-id 4217792
```

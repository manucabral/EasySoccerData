# Match detail tables

In addition to season-wide `matches`, `teams` and `standings`, `esd.load_dataset` can download per-match detail tables (`match_stats`, `lineups`, `player_match_stats`, `match_events`, `shots`) for explicit native `match_ids`.

## Supported detail tables by provider

| Table | `espn` | `sofascore` | `scores365` | `understat` |
| :--- | :---: | :---: | :---: | :---: |
| `"match_stats"` | Yes (`match_ids`) | Yes (`match_ids`) | Yes (`match_ids`) | Yes (season load) |
| `"lineups"` | Yes (`match_ids`) | Yes (`match_ids`) | Yes (`match_ids`) | No |
| `"player_match_stats"` | Yes (`match_ids`) | Yes (`match_ids`) | Yes (`match_ids`) | No |
| `"match_events"` | Yes (`match_ids`) | Yes (`match_ids`) | Yes (`match_ids`) | No |
| `"shots"` | Yes (`match_ids`) | Yes (`match_ids`) | No | Yes (`match_ids`) |

When requesting detail tables on `espn`, `sofascore` or `scores365`:

- `matches` and `teams` are included automatically in `dataset.metadata.tables` so every detail row has its parent fixture and club records.
- `max_match_requests` (default `20`) bounds the number of underlying endpoint calls before HTTP retries.
- `sofascore` and `scores365` require the native `season_id`.

## Team match statistics (`match_stats`)

```py
import esd

stats_ds = esd.load_dataset(
    source="sofascore",
    league="7",
    season=2024,
    season_id=61644,
    tables=("matches", "teams", "match_stats"),
    match_ids=("12173507",),
    cache_dir="./cache",
)

for row in stats_ds.match_stat_records:
    print(
        row.match_id,
        f"Possession: {row.home_possession_pct}% vs {row.away_possession_pct}%",
        f"Shots: {row.home_shots} vs {row.away_shots}",
        f"xG: {row.home_xg} vs {row.away_xg}",
    )
```

## Lineups and player-match statistics (`lineups`, `player_match_stats`)

Requesting `player_match_stats` includes `lineups` automatically so every player statistics row references a validated lineup entry:

```py
import esd

players_ds = esd.load_dataset(
    source="espn",
    league="uefa.champions",
    season=2024,
    tables=("matches", "teams", "lineups", "player_match_stats"),
    match_ids=("704910",),
    cache_dir="./cache",
)

for player in players_ds.player_match_stat_records[:5]:
    print(player.player_name, player.minutes, player.goals, player.assists, player.passes)
```

## Match events (`match_events`)

Normalized events cover goals (`"goal"`, `"own_goal"`, `"penalty_goal"`, `"missed_penalty"`), cards (`"yellow_card"`, `"red_card"`, `"second_yellow_card"`) and substitutions (`"substitution"`), while separating penalty shootout attempts (`is_shootout=True`):

```py
import esd

events_ds = esd.load_dataset(
    source="scores365",
    league="572",
    season=2024,
    season_id=7685,
    tables=("matches", "teams", "match_events"),
    match_ids=("4217792",),
    cache_dir="./cache",
)

for event in events_ds.match_event_records:
    print(event.minute, event.added_minute, event.event_type, event.player_name)
```

## Shot maps (`shots`)

Normalized shot attempts retain each provider's native coordinate system (`"sofascore-native-player"`, `"understat-native"` or `"espn-native-field"`) and xG model:

```py
import esd

shots_ds = esd.load_dataset(
    source="sofascore",
    league="7",
    season=2024,
    season_id=61644,
    tables=("matches", "teams", "shots"),
    match_ids=("12173507",),
    cache_dir="./cache",
)

for shot in shots_ds.shot_records[:5]:
    print(shot.minute, shot.player_name, shot.outcome, shot.xg, shot.xgot, shot.coordinate_system)
```

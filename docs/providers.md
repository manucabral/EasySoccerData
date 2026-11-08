# Providers and limits

Each provider exposes different endpoints, date conventions and native identifiers. `EasySoccerData` keeps selection parameters explicit rather than guessing missing season IDs, timezones or player identities.

## Provider matrix

| Provider | Client class | `source` | Normalized tables | Discovery support |
| :--- | :--- | :--- | :--- | :--- |
| Sofascore | `esd.SofascoreClient` | `"sofascore"` | `matches`, `teams`, `standings`, `match_stats`, `lineups`, `player_match_stats`, `match_events`, `shots` | Competitions (`category_id`), seasons (`index`) |
| ESPN | `esd.ESPNClient` | `"espn"` | `matches`, `teams`, `standings`, `match_stats`, `lineups`, `player_match_stats`, `match_events`, `shots` | Competitions (`listing`), seasons (`index`) |
| 365Scores | `esd.Scores365Client` | `"scores365"` | `matches`, `teams`, `standings`, `match_stats`, `lineups`, `player_match_stats`, `match_events` | Competitions (`search`), seasons (`competition_response`) |
| Understat | `esd.UnderstatClient` | `"understat"` | `matches`, `teams`, `match_stats`, `player_stats`, `shots` | Manual selection |
| FBref | `esd.FBrefClient` | `"fbref"` | `matches`, `teams`, `standings` | Manual selection |
| Transfermarkt | `esd.TransfermarktClient` | `"transfermarkt"` | `teams`, `players`, `market_values`, `transfers` | Competitions (`search_page`), seasons (`selector`) |
| BeSoccer | `esd.BeSoccerClient` | `"besoccer"` | `matches`, `teams`, `standings` | Seasons (`selector`) |
| Promiedos | `esd.PromiedosClient` | `"promiedos"` | `matches`, `teams`, `standings` | Competitions (`date`) |
| Goaloo | `esd.GoalooClient` | `"goaloo"` | `matches`, `teams`, `standings` | Seasons (`index`) |

## Selection contracts and source constraints

| `source` | Selection in `load_dataset` | Source constraints |
| :--- | :--- | :--- |
| `"espn"` | `season` year (calendar discovered from `anchor_date` or July 1); `match_ids` for detail tables | `shots` include only recognized descriptive summary attempts (`xg` and `xgot` are `None`). Detail downloads derive `teams` from match records without `short_name`. |
| `"sofascore"` | Native numeric `season_id`; `match_ids` for detail tables (`max_pages` bounds season pagination) | `match_events` leave `source_period` as `None` (pass `allow_unknown_period=True` to `compare_match_events`). Direct HTTP requests can receive `403` blocks on some networks; `SofascoreClient(use_playwright=True)` can fall back to the system's installed Chrome (`channel="chrome"` or `chrome_path`). |
| `"scores365"` | `start_date`/`end_date` for `matches`; native `season_id` for `standings` and detail tables | No normalized `shots` table. `player_id` uses game `member["id"]` (distinct from `source_athlete_id`). Anonymous placeholder `members` entries without an `"id"` are skipped. |
| `"understat"` | `season` year; `source_timezone` required for naive match kickoffs; `match_ids` required for `shots` | Covers 6 European leagues (`EPL`, `La_liga`, `Bundesliga`, `Serie_A`, `Ligue_1`, `RFPL`) from 2014+. No normalized `standings`, `lineups`, `player_match_stats` or `match_events`. |
| `"fbref"` | `start_date` and `end_date` required for `matches`; `season` year for `standings` | Enforces sequential rate limiting (~3s between requests) and is often gated by Cloudflare challenges on cloud or automated IPs. `FBrefClient(use_playwright=True)` uses the system's installed Chrome (`channel="chrome"` or `chrome_path`) without requiring `playwright install`. |
| `"goaloo"` | Native `source_season` (e.g. `"2024-2025"`) and `source_timezone` | No match-detail tables (`match_stats`, `lineups`, `player_match_stats`, `match_events`, `shots`). |
| `"promiedos"` | `start_date` and `end_date` required for `matches`; `season` year for `standings` | Date-page loader only; no historical season discovery index or match-detail tables. |
| `"besoccer"` | `start_date` and `end_date` required for `matches`; native standings year for `standings` | Standings season option values on multi-year seasons may use the ending year (e.g. `2025` for `2024/25`). No match-detail tables. |
| `"transfermarkt"` | Explicit `club_ids` and/or `player_ids` | Entity/history loader only: `players` reflects current profiles at download time, and `market_values`/`transfers` return full career histories rather than season-filtered slices. |

## Normalized schema (`SCHEMA_VERSION == "6"`)

| Table name | Dataclass model | Primary key fields | Supported providers |
| :--- | :--- | :--- | :--- |
| `"matches"` | `NormalizedMatch` | `("source", "match_id")` | `espn`, `sofascore`, `scores365`, `understat`, `fbref`, `goaloo`, `promiedos`, `besoccer` |
| `"teams"` | `NormalizedTeam` | `("source", "team_id")` | All 9 providers |
| `"standings"` | `NormalizedStanding` | `("source", "competition_id", "season", "source_season_id", "table_id", "table_name", "stage_id", "group_id", "team_id")` | `espn`, `sofascore`, `scores365`, `fbref`, `goaloo`, `promiedos`, `besoccer` |
| `"match_stats"` | `NormalizedMatchStats` | `("source", "match_id")` | `espn`, `sofascore`, `scores365`, `understat` |
| `"lineups"` | `NormalizedLineup` | `("source", "match_id", "team_id", "player_id")` | `espn`, `sofascore`, `scores365` |
| `"player_match_stats"` | `NormalizedPlayerMatchStats` | `("source", "match_id", "team_id", "player_id")` | `espn`, `sofascore`, `scores365` |
| `"match_events"` | `NormalizedMatchEvent` | `("source", "match_id", "event_id" / "source_order")` | `espn`, `sofascore`, `scores365` |
| `"shots"` | `NormalizedShot` | `("source", "match_id", "shot_id" / "source_order")` | `espn`, `sofascore`, `understat` |
| `"player_stats"` | `NormalizedPlayerStats` | `("source", "competition_id", "season", "player_id")` | `understat` |
| `"players"` | `NormalizedPlayer` | `("source", "player_id")` | `transfermarkt` |
| `"market_values"` | `NormalizedMarketValue` | `("source", "player_id", "source_date", "team_id", "source_season_id")` | `transfermarkt` |
| `"transfers"` | `NormalizedTransfer` | `("source", "transfer_id")` | `transfermarkt` |

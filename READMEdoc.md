<h1 align="center">EasySoccerData</h1>

<p align="center">
<img alt="PyPI - Version" src="https://img.shields.io/pypi/v/EasySoccerData?color=00329e">
<img alt="PyPI - Downloads" src="https://img.shields.io/pypi/dm/EasySoccerData?color=009903">
<img alt="GitHub License" src="https://img.shields.io/github/license/manucabral/easysoccerdata">
<img alt="GitHub Actions Workflow Status" src="https://img.shields.io/github/actions/workflow/status/manucabral/easysoccerdata/pylint.yml">
</p>

<p align="center">
A Python library for football fixtures, live scores, standings and player statistics from nine providers.
</p>


# Installation

Dataset features described here target the unreleased 0.2.0 source checkout.
Install from the checkout with `python -m pip install -e ".[full]"` to try them.
The latest published PyPI version may not yet include these APIs.
```
pip install EasySoccerData
```

# Usage

## Sofascore
```py
import esd

client = esd.SofascoreClient()
events = client.get_events(live=True)
for event in events:
    print(event)
```

[How to search for matches, teams, tournaments, and players](https://github.com/manucabral/EasySoccerData/blob/main/examples/sofascore/search_matchs.py)

[How to get tournament brackets](https://github.com/manucabral/EasySoccerData/blob/main/examples/sofascore/tournament_bracket.py)

[How to get live match statistics](https://github.com/manucabral/EasySoccerData/blob/main/examples/sofascore/get_live_matchs.py)


[Sofascore examples](https://github.com/manucabral/EasySoccerData/tree/main/examples/sofascore/)

## FBRef
```py
import esd

client = esd.FBrefClient()
matchs = client.get_matchs()
for match in matchs:
    print(match)
```

[FBref examples](https://github.com/manucabral/EasySoccerData/tree/main/examples/fbref/)

## Promiedos
```py
import esd

client = esd.PromiedosClient()
events = client.get_events()
for event in events:
    print(event)
```

[Promiedos examples](https://github.com/manucabral/EasySoccerData/tree/main/examples/promiedos/)

## Goaloo
```py
import esd

client = esd.GoalooClient()
standings = client.get_standings(36)
```

[Goaloo examples](https://github.com/manucabral/EasySoccerData/tree/main/examples/goaloo/)

## 365Scores
```py
import esd

client = esd.Scores365Client()
games = client.get_games("today")
```

[365Scores examples](https://github.com/manucabral/EasySoccerData/tree/main/examples/scores365/)

## Understat
```py
import esd

client = esd.UnderstatClient()
matches = client.get_league_matches("EPL", 2024)
```

[Understat examples](https://github.com/manucabral/EasySoccerData/tree/main/examples/understat/)

## Transfermarkt
```py
import esd

client = esd.TransfermarktClient()
player = client.get_player(28003)
```

[Transfermarkt examples](https://github.com/manucabral/EasySoccerData/tree/main/examples/transfermarkt/)

## ESPN
```py
import esd

client = esd.ESPNClient()
matches = client.get_scoreboard("arg.1")
```

[ESPN examples](https://github.com/manucabral/EasySoccerData/tree/main/examples/espn/)

## BeSoccer
```py
import esd

client = esd.BeSoccerClient()
matches = client.get_matches("today")
```

[BeSoccer examples](https://github.com/manucabral/EasySoccerData/tree/main/examples/besoccer/)


## Pandas

Install with `pip install "EasySoccerData[pandas]"`. pandas remains optional
and is imported only when `esd.to_dataframe()` is called.

```py
import esd

client = esd.ESPNClient()
games = esd.to_dataframe(
    client.get_scoreboard("arg.1"),
    flatten=True,
    convert_dtypes=True,
    dtypes={"id": "string", "home_team.score": "Int64"},
    datetime_columns={"date": None},
)
for table in client.get_standings("arg.1"):
    standings = esd.to_dataframe(table.rows, flatten=True, convert_dtypes=True)
```

Flattening creates columns such as `home_team.name`; lists stay in cells.
Nullable type inference is optional. Explicit `dtypes` fix types even for
all-missing columns. Dates are converted only when declared: `None` parses
strings/datetime objects, `"s"` means Unix seconds and `"ms"` milliseconds.
Date output uses UTC and naive dates are treated as UTC. Invalid dates raise.
Missing values remain missing and zero remains zero. Provider field names are
preserved. Default calls keep nested dictionaries and normal pandas inference.

Empty input has no columns unless a schema is declared. Unknown columns in
nonempty input raise `KeyError`. Date columns belong only in `datetime_columns`.

## Common tables

`esd.normalize_match()`, `esd.normalize_team()` and `esd.normalize_standings()`
adapt supported provider models into flat `NormalizedMatch`, `NormalizedTeam`
and `NormalizedStanding` records. Existing client return types stay unchanged.
Unsupported provider models raise `TypeError`.

```py
records = [
    esd.normalize_match(match, competition_id="arg.1", season=2026)
    for match in client.get_scoreboard("arg.1")
]
matches = esd.normalized_to_dataframe(records, table="matches")
```

Understat adds match/team adapters and `normalize_match_stats()`,
`normalize_player_stats()` and `normalize_shot()`. The corresponding models are
`NormalizedMatchStats`, `NormalizedPlayerStats` and `NormalizedShot`.
Shots preserve native coordinates and player statistics retain native club-name
strings without resolving team identities.

The normalized DataFrame tables are `matches`, `teams`, `standings`,
`match_stats`, `player_stats`, `shots`, `players`, `market_values`, `transfers`,
`lineups`, `player_match_stats` and `match_events`. They
have fixed columns and types even when empty: nullable strings for identifiers
and names, `Int64` for counts, `Float64` for metrics and UTC nanosecond datetimes for `kickoff`.
`DataFrame.attrs` reports `schema_version="5"` and the table name.
Version `1`–`4` Parquet snapshots remain readable. Absent statistic/event columns are
null and tables introduced later stay unselected.

Join entities using both `source` and their source-local ID. Adapters preserve
names without matching entities across providers. The caller-supplied `season`
label is separate from 365Scores' `source_season_id`; native competition IDs
cannot be replaced with conflicting values. Standings retain table, stage and
group context. Source status codes/text retain their original semantics.

Unknown values stay null, subject to defaults already applied by provider
parsers. Invalid or timezone-naive kickoff dates raise. Adapters require no
pandas and make no network requests; DataFrame export uses the optional extra.

`esd.validate_dataset(dataset)` returns errors and warnings about normalized
records, references and task coverage. Validation works without pandas or PyArrow
and does not change or fetch data.

ESPN, 365Scores and Sofascore accept `tables=["match_stats"]` with explicit
`match_ids` and a `max_match_requests` budget. These detail queries return the
selected matches and teams, nullable counts and possession without downloading
a season calendar. 365Scores and Sofascore require native `season_id`. Counts,
periods and xG retain their documented source semantics.

`esd.compare_match_statistics(left, right, identities=...)` compares statistics
for uniquely linked matches without downloads or optional dependencies. Results
retain missing values, source periods, original fetch times, partial errors and
unmatched/ambiguous IDs. Cross-source xG/forecast models remain separate.
`report.to_dataframe()` requires the pandas extra.

`compare_match_events(left, right, identities=...)` compares ESPN/365Scores
events after explicit match and player linkage. Known differences, unknown
observations, ambiguous candidates and failed/empty event tasks remain separate.
`IdentityMap` accepts caller-reviewed `player` aliases and can be extended with
`with_aliases()` without changing the original map. The bundled catalog still
supplies only competition/team aliases. See the
[event comparison guide](https://github.com/manucabral/EasySoccerData/blob/release/0.2.0/guides/datasets.md#compare-match-events).

ESPN, 365Scores and Sofascore expose `match_events` for explicit IDs. ESPN/365Scores
share summary/game detail with player tables. Sofascore shares event context,
then reads incidents and any selected lineups/statistics separately.
Native periods, added time, annulment flags, participant IDs and shootout counters
remain separate. ESPN includes reviewed
commentary plays missing from `keyEvents`, without resolving names to IDs.
The [event guide](https://github.com/manucabral/EasySoccerData/blob/release/0.2.0/guides/datasets.md#match-events)
documents field meanings and collection limits. Run
`python examples/datasets/match_events_offline.py` for all three artificial sources.

ESPN, 365Scores and Sofascore accept `lineups` and `player_match_stats` for
explicit match IDs, alongside optional team match totals. Lineups retain native
positions, formations, source status and nullable starter/captain/confirmation
flags. Player match rows preserve observed metrics and separate 365Scores member
and athlete IDs. Missing minutes remain null. Player-season `player_stats`
retains its existing Understat scope. Both new tables use the base installation;
DataFrame properties and snapshot storage keep their independent extras.

`esd.get_discovery_capabilities()` lists competition and season discovery support
for all nine providers. `list_competitions()` and `list_seasons()` return native
selectors with their query scope and original fetch timestamp, without pandas.
Transfermarkt discovery preserves league/cup routes and search pages. BeSoccer
returns its native standings year options. The examples include a 365Scores
discovery-to-download flow with validation and optional snapshot verification.

`esd.get_catalog()` reads a versioned sample of reviewed competition/team IDs
for ESPN and 365Scores. It resolves canonical IDs, names and declared aliases
without requests. Season discovery remains explicit and preserves native
selectors. Catalogs can build an `IdentityMap`, accept nonconflicting additions
and save/open caller-owned JSON without optional dependencies.

.. include:: guides/datasets.md

# Contributing

For bug reports, include the provider, method, arguments and traceback. Remove
proxy credentials and tokens from logs. Add a response fixture and an offline
regression test when submitting a parser fix.

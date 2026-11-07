<h1 align="center">EasySoccerData</h1>

<p align="center">
<img alt="PyPI - Version" src="https://img.shields.io/pypi/v/EasySoccerData?color=00329e">
<img alt="PyPI - Downloads" src="https://img.shields.io/pypi/dm/EasySoccerData?color=009903">
<img alt="GitHub License" src="https://img.shields.io/github/license/manucabral/easysoccerdata">
<img alt="GitHub Actions Workflow Status" src="https://img.shields.io/github/actions/workflow/status/manucabral/easysoccerdata/pylint.yml">
</p>

<p align="center">
A simple python package for extracting real-time soccer/football data from diverse online sources, providing essential statistics and insights.
</p>


> [!IMPORTANT]  
> Currently in the early development phase. Please take this into consideration.

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


Check out [Sofascore module examples](https://github.com/manucabral/EasySoccerData/tree/main/examples/sofascore/)

## FBRef
```py
import esd

client = esd.FBrefClient()
matchs = client.get_matchs()
for match in matchs:
    print(match)
```

Check out [FBref module examples](https://github.com/manucabral/EasySoccerData/tree/main/examples/fbref/)

## Promiedos
```py
import esd

client = esd.PromiedosClient()
events = client.get_events()
for event in events:
    print(event)
```

Check out [Promiedos module examples](https://github.com/manucabral/EasySoccerData/tree/main/examples/promiedos/)

## Goaloo
```py
import esd

client = esd.GoalooClient()
standings = client.get_standings(36)
```

Check out [Goaloo module examples](https://github.com/manucabral/EasySoccerData/tree/main/examples/goaloo/)

## 365Scores
```py
import esd

client = esd.Scores365Client()
games = client.get_games("today")
```

Check out [365Scores module examples](https://github.com/manucabral/EasySoccerData/tree/main/examples/scores365/)

## Understat
```py
import esd

client = esd.UnderstatClient()
matches = client.get_league_matches("EPL", 2024)
```

Check out [Understat module examples](https://github.com/manucabral/EasySoccerData/tree/main/examples/understat/)

## Transfermarkt
```py
import esd

client = esd.TransfermarktClient()
player = client.get_player(28003)
```

Check out [Transfermarkt module examples](https://github.com/manucabral/EasySoccerData/tree/main/examples/transfermarkt/)

## ESPN
```py
import esd

client = esd.ESPNClient()
matches = client.get_scoreboard("arg.1")
```

Check out [ESPN module examples](https://github.com/manucabral/EasySoccerData/tree/main/examples/espn/)

## BeSoccer
```py
import esd

client = esd.BeSoccerClient()
matches = client.get_matches("today")
```

Check out [BeSoccer module examples](https://github.com/manucabral/EasySoccerData/tree/main/examples/besoccer/)


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
`match_stats`, `player_stats`, `shots`, `players`, `market_values` and `transfers`. They
have fixed columns and types even when empty: nullable strings for identifiers
and names, `Int64` for counts, `Float64` for metrics and UTC nanosecond datetimes for `kickoff`.
`DataFrame.attrs` reports `schema_version="1"` and the table name.

Join entities using both `source` and their source-local ID. Adapters preserve
names without matching entities across providers. The caller-supplied `season`
label is separate from 365Scores' `source_season_id`; native competition IDs
cannot be replaced with conflicting values. Standings retain table, stage and
group context. Source status codes/text retain their original semantics.

Unknown values stay null, subject to defaults already applied by provider
parsers. Invalid or timezone-naive kickoff dates raise. Adapters require no
pandas and make no network requests; DataFrame export uses the optional extra.

.. include:: guides/datasets.md

# Supported modules

| Name | Implemented |
| :---  | :---: |
| Sofascore   | ✔️ |
| FBref    | ✔️ |
| Promiedos    | ✔️ |
| Goaloo    | ✔️ |
| 365Scores    | ✔️ |
| Understat    | ✔️ |
| Transfermarkt    | ✔️ |
| ESPN    | ✔️ |
| BeSoccer    | ✔️ |
...
> Keep in mind that it is still under active development.

### Contributions
All contributions, bug reports or fixes and ideas are welcome.

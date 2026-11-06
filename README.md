<h1 align="center">EasySoccerData</h1>

<p align="center">
<img alt="PyPI - Version" src="https://img.shields.io/pypi/v/EasySoccerData?color=00329e">
<img alt="Pepy Total Downloads" src="https://img.shields.io/pepy/dt/EasySoccerData?color=009903">
<img alt="GitHub License" src="https://img.shields.io/github/license/manucabral/easysoccerdata">
<img alt="GitHub Actions Workflow Status" src="https://img.shields.io/github/actions/workflow/status/manucabral/easysoccerdata/pylint.yml">
</p>

<p align="center">
A simple python package for extracting real-time soccer/football data from diverse online sources, providing essential statistics and insights.
</p>


# Installation
```
pip install EasySoccerData
```

## Development
```
git clone https://github.com/manucabral/EasySoccerData.git
cd EasySoccerData
pip install -e .[dev]
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
> [!WARNING]
> FBRef is not available in the latest PyPI release yet.
> 
> It is currently available only in the development version from the repository.
> 
> Check out [FBref module examples](https://github.com/manucabral/EasySoccerData/tree/main/examples/fbref/)

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
league = client.get_league(36)          # 36 = English Premier League
standings = client.get_standings(36)
for row in standings[:5]:
    print(row.rank, row.team.name, row.points)
```

Check out [Goaloo module examples](https://github.com/manucabral/EasySoccerData/tree/main/examples/goaloo/)

## 365Scores
```py
import esd

client = esd.Scores365Client()
games = client.get_games("today")
standings = client.get_standings(72)    # 72 = Liga Profesional Argentina
for row in standings[0].rows[:5]:
    print(row.position, row.team.name, row.points)
```

## Understat
```py
import esd

client = esd.UnderstatClient()
matches = client.get_league_matches("EPL", 2024)
shots = client.get_match_shots(26602)
```

## Transfermarkt
```py
import esd

client = esd.TransfermarktClient()
player = client.get_player(28003)
print(player.name, player.market_value_display)
transfers = client.get_player_transfers(28003)
```

## ESPN
```py
import esd

client = esd.ESPNClient()
matches = client.get_scoreboard("arg.1")
standings = client.get_standings("arg.1")
```

## BeSoccer
```py
import esd

client = esd.BeSoccerClient()
matches = client.get_matches("today")
standings = client.get_standings("torneo_final")
```

## Parallel fetching

Fetch multiple leagues or matches concurrently with `fetch_many`:

```py
from functools import partial

import esd
from esd.utils import fetch_many

client = esd.GoalooClient()
standings = fetch_many(
    [partial(client.get_standings, league) for league in (36, 31, 8)]
)
```

Requests use a pooled HTTP session, cache recent responses briefly, and retry transient failures automatically.

## Demo
Simple demonstration of a live table using Sofascore module (see [source code](https://github.com/manucabral/EasySoccerData/blob/main/examples/sofascore/live_table.py))
<p align="center">
<img src="https://github.com/manucabral/EasySoccerData/blob/main/assets/sofascore-live-table.gif" width="550" title="LiveTableUsingSofascore">
</p>

# Documentation
For the full documentation, please visit the [Documentation Page](https://manucabral.github.io/EasySoccerData/esd.html)

If you have any questions or need further assistance, feel free to open an issue.

## Supported modules
| Name | PyPI version | Repository version |
| :--- | :---: | :---: |
| Sofascore | ✅ | ✅ |
| Promiedos | ✅ | ✅ |
| FBRef | ❌ | ✅ |
| Goaloo | ❌ | ✅ |
| 365Scores | ❌ | ✅ |
| Understat | ❌ | ✅ |
| Transfermarkt | ❌ | ✅ |
| ESPN | ❌ | ✅ |
| BeSoccer | ❌ | ✅ |

> Keep in mind that it is still under active development.

# Disclaimer
The data provided in this repository is gathered from various external sources and is intended solely for informational purposes. This software is distributed "as-is," without any warranties or guarantees. Users are solely responsible for ensuring that their use of this data complies with the terms of service of the respective data sources and all applicable laws.

The developers of this project assume no liability for any misuse, legal issues, or damages arising from the use of the data or software.


# Contributions
All contributions, bug reports, fixes, and ideas are welcome.

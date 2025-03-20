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

## Demo
Simple demonstration of a live table using Sofascore module (see [source code](https://github.com/manucabral/EasySoccerData/blob/main/examples/live_table.py))
<p align="center">
<img src="https://github.com/manucabral/EasySoccerData/blob/main/assets/sofascore-live-table.gif" width="550" title="LiveTableUsingSofascore">
</p>

# Documentation
For the full documentation, please visit the [Documentation Page](https://manucabral.github.io/EasySoccerData/esd.html)

If you have any questions or need further assistance, feel free to open an issue.

## Supported modules

| Name | Implemented |
| :---  | :---: |
| Sofascore   | ✔️ |
| FBref    | ✔️ |
| Promiedos    | ✔️ |
> Keep in mind that it is still under active development.

# Disclaimer
This software is provided "as-is" without any warranties. Use it at your own risk and ensure you comply with all applicable laws, regulations, and the terms of service of any websites and APIs involved.

The developers are not responsible for any damages or consequences arising from its use.


# Constributions
All constributions, bug reports or fixes and ideas are welcome.

# Discovery and catalog

Before calling `load_dataset`, you can discover competition and season identifiers dynamically with `list_competitions` and `list_seasons`, or look up reviewed cross-provider references from the bundled `FootballCatalog`.

## Competition and season discovery

Inspect which discovery endpoints a provider supports using `esd.get_discovery_capabilities()`:

```py
import esd

caps = esd.get_discovery_capabilities()
for source, info in caps.items():
    print(f"{source:15s} competitions={info.competitions!s:12s} seasons={info.seasons!s}")
```

Discover competitions and seasons on supported providers:

```py
import esd

# ESPN: list soccer leagues from dropdown and list native season years
espn_comps = esd.list_competitions("espn", query="Champions", cache_dir="./cache")
espn_seasons = esd.list_seasons("espn", "uefa.champions", cache_dir="./cache")

# Sofascore: list tournaments in a football category (e.g. 1465 = UEFA, 1 = England)
sofascore_comps = esd.list_competitions("sofascore", category_id=1465, cache_dir="./cache")
sofascore_seasons = esd.list_seasons("sofascore", 7, cache_dir="./cache")

# 365Scores: search football competitions by query string
scores365_comps = esd.list_competitions("scores365", query="Champions League", cache_dir="./cache")
scores365_seasons = esd.list_seasons("scores365", 572, cache_dir="./cache")
```

## Reviewed catalog (`get_catalog`)

`esd.get_catalog()` returns an immutable `FootballCatalog` with reviewed competition and team references across `espn`, `sofascore`, `scores365` and additional providers:

```py
import esd

catalog = esd.get_catalog()

# Resolve by canonical ID, display name or alias
ucl = catalog.competition("uefa-champions-league")
for ref in ucl.references:
    print(ref.source, ref.source_id, ref.source_url)

arsenal = catalog.team("Arsenal")
print(arsenal.for_source("sofascore").source_id)  # "42"
```

## Build `load_dataset` options from discovered seasons

`catalog.list_seasons()` and `catalog.dataset_options()` turn a discovered `SeasonInfo` into validated keyword arguments for `load_dataset()`:

```py
import esd

catalog = esd.get_catalog()
seasons = catalog.list_seasons("uefa-champions-league", "sofascore", cache_dir="./cache")
chosen = next(s for s in seasons.seasons if s.source_season == "24/25")

options = catalog.dataset_options("uefa-champions-league", chosen, year=2024)
# {'source': 'sofascore', 'league': '7', 'season': 2024, 'season_id': '61644'}
```

## Extend and save custom catalogs

Use `catalog.with_entries()` to add competitions, teams or provider references without modifying the bundled catalog, and persist the result with `save_json()` and `open_catalog()`:

```py
from datetime import datetime, timezone
import esd

catalog = esd.get_catalog()
extended = catalog.with_entries(
    teams=[
        esd.CatalogTeam(
            canonical_id="inter-miami",
            name="Inter Miami CF",
            aliases=("Inter Miami",),
            references=(
                esd.CatalogReference(
                    source="espn",
                    source_id="20232",
                    source_url="https://www.espn.com/soccer/team/_/id/20232",
                    verified_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
                ),
            ),
        )
    ]
)
extended.save_json("./custom-catalog.json")
reloaded = esd.open_catalog("./custom-catalog.json")
```

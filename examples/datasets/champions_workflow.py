"""Download Champions match/player/event tables, compare sources and reopen offline.

--demo uses artificial native responses and runs the cache twice without HTTP.
Live mode needs explicit native match/season IDs. Sofascore is optional. The
base installation handles records/comparisons/cache; storage needs [parquet].
"""

import argparse
import json
import math
import os
import sys
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import asdict
from importlib.util import find_spec
from itertools import combinations
from pathlib import Path
from tempfile import TemporaryDirectory
from time import sleep
from unittest.mock import patch

import esd

SOURCES = ("espn", "scores365", "sofascore")
LEAGUES = {"espn": "uefa.champions", "scores365": "572", "sofascore": "7"}
COSTS = {"espn": 1, "scores365": 2, "sofascore": 4}
TABLES = ("matches", "teams", "match_stats", "lineups", "player_match_stats", "match_events")
DEFAULT_IDENTITIES = Path(__file__).with_name("champions_workflow_identities.json")


@contextmanager
def workflow_directory(prefix, *, parent=None):
    """Retry transient Windows directory-not-empty cleanup at most twice."""
    temporary = TemporaryDirectory(prefix=prefix, dir=parent)
    try:
        yield Path(temporary.name)
    finally:
        for attempt in range(3):
            try:
                temporary.cleanup()
            except OSError as exc:
                if getattr(exc, "winerror", None) != 145 or attempt == 2:
                    raise
                sleep(0.05 * (attempt + 1))
            else:
                break


def positive(value):
    if not value.isascii() or not value.isdecimal() or int(value) < 1:
        raise argparse.ArgumentTypeError("Expected a positive native numeric ID")
    return str(int(value))


def nonnegative(value):
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise argparse.ArgumentTypeError("Expected a finite nonnegative number")
    return number


def read_identities(path):
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list) or any(not isinstance(item, dict) for item in raw):
        raise ValueError("Identities must be a JSON list of EntityAlias objects")
    try:
        return esd.IdentityMap(esd.EntityAlias(**item) for item in raw)
    except TypeError as exc:
        raise ValueError(f"Invalid identity entry: {exc}") from exc


def default_settings(sources, *, allow_unknown_period=False, minute_tolerance=1, tolerance_seconds=300):
    return {"format": "easysoccerdata-champions-workflow", "format_version": 1, "sources": list(sources),
            "events": {"allow_unknown_period": allow_unknown_period, "minute_tolerance": minute_tolerance,
                       "tolerance_seconds": tolerance_seconds,
                       "event_types": ["goal", "own_goal", "penalty_scored", "penalty_missed", "yellow_card", "red_card", "second_yellow_card", "substitution"],
                       "period_aliases": []},
            "players": {"metrics": ["minutes", "goals", "assists", "shots", "shots_on_target", "xg", "xa", "source_rating"],
                        "tolerances": {}, "position_aliases": [], "tolerance_seconds": tolerance_seconds},
            "team_statistics": {"metrics": ["home_shots", "away_shots", "home_possession_pct", "away_possession_pct", "home_xg", "away_xg"],
                                "tolerances": {}, "tolerance_seconds": tolerance_seconds}}


def aliases(values, label):
    if not isinstance(values, list) or any(not isinstance(row, list) or len(row) != 3
                                         or any(not isinstance(value, str) for value in row) for row in values):
        raise ValueError(f"Invalid saved {label} aliases")
    result = {}
    for source, native, canonical in values:
        if (source, native) in result:
            raise ValueError(f"Duplicate saved {label} alias")
        result[source, native] = canonical
    return result


def comparison_options(settings):
    expected = {"format", "format_version", "sources", "events", "players", "team_statistics"}
    if (not isinstance(settings, dict) or set(settings) != expected
            or settings["format"] != "easysoccerdata-champions-workflow"
            or type(settings["format_version"]) is not int or settings["format_version"] != 1
            or settings["sources"] not in (["espn", "scores365"], list(SOURCES))):
        raise ValueError("Invalid workflow format/version/source selection")
    shapes = {"events": {"allow_unknown_period", "minute_tolerance", "tolerance_seconds", "event_types", "period_aliases"},
              "players": {"metrics", "tolerances", "position_aliases", "tolerance_seconds"},
              "team_statistics": {"metrics", "tolerances", "tolerance_seconds"}}
    result = {}
    for name, keys in shapes.items():
        if not isinstance(settings[name], dict) or set(settings[name]) != keys:
            raise ValueError(f"Invalid saved {name} settings")
        result[name] = dict(settings[name])
    result["events"]["period_aliases"] = aliases(settings["events"]["period_aliases"], "period")
    result["players"]["position_aliases"] = aliases(settings["players"]["position_aliases"], "position")
    return result


def compare_sources(datasets, identities, settings):
    options = comparison_options(settings)
    if [item.metadata.source for item in datasets] != settings["sources"]:
        raise ValueError("Workflow source order differs from saved selection")
    for dataset in datasets:
        if dataset.metadata.league != LEAGUES[dataset.metadata.source] or not set(TABLES) <= set(dataset.metadata.tables):
            raise ValueError("Expected a Champions snapshot selecting all workflow tables")
    reports = {}
    for left, right in combinations(datasets, 2):
        events = esd.compare_match_events(left, right, identities=identities, **options["events"])
        players = esd.compare_match_players(left, right, identities=identities, **options["players"])
        statistics = esd.compare_match_statistics(left, right, identities=identities, **options["team_statistics"])
        indexes = [{row.match_id: row for row in dataset.match_records} for dataset in (left, right)]
        fixtures = []
        for link in events.linkage.links:
            first, second = indexes[0][link.left_match_id], indexes[1][link.right_match_id]
            different, unknown = [], []
            for field in ("home_score", "away_score", "kickoff"):
                values = (getattr(first, field), getattr(second, field))
                if any(value is None for value in values):
                    unknown.append(field)
                elif values[0] != values[1]:
                    different.append(field)
            fixtures.append({"left": first, "right": second, "differences": tuple(different), "unknown_fields": tuple(unknown)})
        reports[f"{left.metadata.source}--{right.metadata.source}"] = {
            "events": events, "players": players, "team_statistics": statistics, "matches": tuple(fixtures),
        }
    return reports


def saved_settings(settings, reports):
    """Pin resolved period defaults so reopening uses the original rules."""
    result = deepcopy(settings)
    if reports:
        result["events"]["period_aliases"] = [list(row) for row in next(iter(reports.values()))["events"].period_aliases]
    return result


def json_value(value):
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    return value.isoformat()


def save_bundle(destination, datasets, identities, settings, reports):
    destination = destination.absolute()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with workflow_directory(".esd-champions-workflow-", parent=destination.parent) as temporary:
        staging = temporary / "workflow"
        staging.mkdir()
        for dataset in datasets:
            target = dataset.save(staging / dataset.metadata.source)
            if esd.open_dataset(target) != dataset:
                raise esd.DatasetFormatError("Reopened workflow snapshot differs from the download")
        for name, value in (("identities", [asdict(alias) for alias in identities.aliases]),
                            ("options", saved_settings(settings, reports)), ("comparison", reports)):
            (staging / f"{name}.json").write_text(json.dumps(value, default=json_value, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        if destination.exists() or destination.is_symlink():
            raise FileExistsError(f"Workflow destination already exists: {destination}")
        os.rename(staging, destination)


def demo_inputs():
    """Artificial responses/aliases, unrelated to the IDs of any real fixture."""
    from esd.espn.endpoints import ESPNEndpoints
    from esd.scores365.endpoints import Scores365Endpoints
    from esd.sofascore.endpoints import SofascoreEndpoints

    espn = {"header": {"id": "1", "league": {"slug": "uefa.champions"}, "season": {"year": 2026},
                       "competitions": [{"id": "1", "date": "2026-11-03T20:00:00Z", "competitors": [
                           {"homeAway": side, "team": {"id": team}, "score": str(score)} for side, team, score in (("home", "10", 1), ("away", "20", 0))]}]},
            "rosters": [{"team": {"id": "10"}, "roster": [
                {"athlete": {"id": "101", "displayName": "Artificial scorer"}, "starter": True, "position": {"abbreviation": "F"},
                 "stats": [{"name": "totalGoals", "value": 1}, {"name": "totalShots", "value": 3}, {"name": "shotsOnTarget", "value": 2}]}]}],
            "boxscore": {"teams": [{"team": {"id": "10"}, "statistics": [{"name": "totalShots", "displayValue": "12"}]}]},
            "keyEvents": [{"id": "event-1", "type": {"id": "70"}, "period": {"number": 2}, "shootout": False,
                           "clock": {"displayValue": "59'", "value": 3540}, "team": {"id": "10"},
                           "participants": [{"athlete": {"id": "101"}}]}]}
    game = {"id": 2, "competitionId": 572, "seasonNum": 228, "sportId": 1, "startTime": "2026-11-03T20:00:00Z",
            "hasLineups": True, "members": [{"id": 201, "athleteId": 999, "competitorId": 30, "name": "Artificial scorer"}],
            "homeCompetitor": {"id": 30, "score": 1, "lineups": {"members": [{"id": 201, "status": 1, "stats": [
                {"type": 27, "value": "1"}, {"type": 3, "value": "4"}, {"type": 4, "value": "2"},
                {"type": 30, "value": "90"}, {"type": 76, "value": "0.5"}]}]}},
            "awayCompetitor": {"id": 40, "score": 0, "lineups": {"members": []}},
            "events": [{"order": 1, "eventType": {"id": 1, "subTypeId": 1}, "gameTime": 60,
                        "gameTimeDisplay": "60'", "stageId": 9, "competitorId": 30, "playerId": 201}]}
    sofa = {"event": {"id": 3, "season": {"id": 228}, "tournament": {"uniqueTournament": {"id": 7}},
                      "startTimestamp": 1793736000, "status": {"type": "finished"}, "homeTeam": {"id": 50}, "awayTeam": {"id": 60},
                      "homeScore": {"current": 1}, "awayScore": {"current": 0}}}
    scores, sofas = Scores365Endpoints(timezone_name="UTC"), SofascoreEndpoints()
    responses = {
        ESPNEndpoints().summary("1", "uefa.champions"): espn,
        scores.game_detail(2): {"game": game},
        scores.game_stats(2): {"games": [game], "actualGameStatistics": {"filterId": -1},
                               "statistics": [{"id": 3, "competitorId": 30, "value": "13"}]},
        sofas.event_endpoint(3): sofa,
        sofas.match_lineups_endpoint(3): {"confirmed": True, "home": {"players": [{"player": {"id": 301, "position": "F"},
            "substitute": False, "statistics": {"minutesPlayed": 90, "goals": 1, "onTargetScoringAttempt": 2,
                                                "expectedGoals": 0.4, "rating": 7.2}}]}, "away": {"players": []}},
        sofas.match_events_endpoint(3): {"incidents": [{"id": 91, "incidentType": "goal", "incidentClass": "regular",
            "time": 59, "isHome": True, "player": {"id": 301}, "rescinded": False}]},
        sofas.match_stats_endpoint(3): {"statistics": [{"period": "ALL", "groups": [{"statisticsItems": [
            {"key": "totalShotsOnGoal", "homeValue": 13, "awayValue": 4}]}]}]},
    }
    selections, entries = {}, []
    for source, identifier, competition, home, away, player in (
        ("espn", "1", "uefa.champions", "10", "20", "101"),
        ("scores365", "2", "572", "30", "40", "201"), ("sofascore", "3", "7", "50", "60", "301"),
    ):
        selections[source] = {"identifier": identifier, "year": 2026, "season_id": None if source == "espn" else "228"}
        entries.extend(esd.EntityAlias(kind, canonical, source, native) for kind, canonical, native in (
            ("competition", "champions", competition), ("team", "home", home), ("team", "away", away), ("player", "scorer", player)))
    return selections, esd.IdentityMap(entries), responses


def download(selections, cache_dir, refresh, *, request_delay=None):
    timing = {"request_delay": request_delay} if request_delay is not None else {}
    return [esd.load_dataset(source=source, league=LEAGUES[source], season=selection["year"], season_id=selection["season_id"],
                            match_ids=[selection["identifier"]], tables=TABLES, max_match_requests=COSTS[source],
                            cache_dir=cache_dir, refresh=refresh, on_error="collect", **timing) for source, selection in selections.items()]


def display(datasets, reports, limit, pandas):
    for dataset in datasets:
        validation = esd.validate_dataset(dataset)
        print(dataset.metadata.source, "| Complete:", dataset.complete, "| Valid:", validation.valid,
              "| Matches/lineups/player stats/events:", len(dataset.match_records), len(dataset.lineup_records),
              len(dataset.player_match_stat_records), len(dataset.match_event_records))
        print("Original fetches:", dataset.metadata.response_fetched_at, "| Cached:", dataset.metadata.cached_tasks)
        for issue in dataset.errors:
            print(f"{dataset.metadata.source} {issue.step} {issue.target}: {issue.error_type}: {issue.message}", file=sys.stderr)
    for name, group in reports.items():
        print(name, "| Linked matches:", len(group["matches"]), "| Event differences/unresolved:",
              len(group["events"].differences), len(group["events"].unresolved), "| Lineup differences/unresolved:",
              len(group["players"].differences), len(group["players"].unresolved))
        print("Team/player metric differences:", len(group["team_statistics"].differences), len(group["players"].statistic_differences))
        for row in group["events"].rows[:limit]:
            print("Event:", row.status, row.reason, "| Differences:", row.differences, "| Unknown:", row.unknown_fields)
        for fixture in group["matches"][:limit]:
            print("Match:", fixture["left"].match_id, fixture["right"].match_id, "| Differences:", fixture["differences"], "| Unknown:", fixture["unknown_fields"])
        if pandas:
            for frame in (group["events"].to_dataframe(), group["players"].to_dataframe(),
                          group["players"].to_dataframe("statistics"), group["team_statistics"].to_dataframe()):
                print(frame.head(limit))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true")
    for source in SOURCES:
        parser.add_argument(f"--{source}-match-id", type=positive)
    parser.add_argument("--espn-season", type=int)
    parser.add_argument("--year", type=int, help="Caller year label for 365Scores/Sofascore")
    parser.add_argument("--scores365-season-id", type=positive)
    parser.add_argument("--sofascore-season-id", type=positive)
    parser.add_argument("--identities", type=Path)
    parser.add_argument("--allow-unknown-period", action="store_true", default=None)
    parser.add_argument("--minute-tolerance", type=int)
    parser.add_argument("--kickoff-tolerance", type=nonnegative)
    parser.add_argument("--max-match-requests", type=int, help="Total endpoint-read budget, before retries")
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--pandas", action="store_true")
    parser.add_argument("--parquet", action="store_true", help="Verify a temporary snapshot bundle in demo mode")
    parser.add_argument("--limit", type=int, default=3)
    storage = parser.add_mutually_exclusive_group()
    storage.add_argument("--output-dir", type=Path, help="New directory for source snapshots, identities, options and report")
    storage.add_argument("--open-dir", type=Path, help="Recompute a saved workflow without HTTP")
    args = parser.parse_args(argv)
    native = (args.espn_match_id, args.scores365_match_id, args.sofascore_match_id, args.espn_season,
              args.year, args.scores365_season_id, args.sofascore_season_id, args.identities)
    if args.limit < 1 or args.minute_tolerance is not None and args.minute_tolerance < 0:
        parser.error("--limit must be positive and --minute-tolerance nonnegative")
    if args.open_dir is not None and (args.demo or args.refresh or any(value is not None for value in (
        *native, args.allow_unknown_period, args.minute_tolerance, args.kickoff_tolerance, args.max_match_requests, args.cache_dir,
    ))):
        parser.error("--open-dir cannot be combined with downloads or external comparison settings")
    if args.demo and any(value is not None for value in native):
        parser.error("--demo uses artificial selectors and identities")
    if args.parquet and not args.demo:
        parser.error("--parquet verifies a temporary demo bundle; live storage uses --output-dir")
    try:
        if (args.parquet or args.output_dir is not None or args.open_dir is not None) and find_spec("pyarrow") is None:
            raise ImportError("Snapshot storage requires EasySoccerData[parquet]")
        if args.pandas and find_spec("pandas") is None:
            raise ImportError("DataFrame display requires EasySoccerData[pandas]")
        if args.output_dir is not None:
            args.output_dir = args.output_dir.expanduser()
            if args.output_dir.exists() or args.output_dir.is_symlink():
                raise FileExistsError(f"Workflow destination already exists: {args.output_dir}")
        if args.open_dir is not None:
            directory = args.open_dir.expanduser()
            settings = json.loads((directory / "options.json").read_text(encoding="utf-8"))
            comparison_options(settings)
            identities = read_identities(directory / "identities.json")
            datasets = [esd.open_dataset(directory / source) for source in settings["sources"]]
        else:
            if args.demo:
                selections, identities, responses = demo_inputs()
            else:
                required = (args.espn_match_id, args.scores365_match_id, args.espn_season, args.year, args.scores365_season_id)
                if any(value is None for value in required) or not all(1000 <= year <= 9999 for year in (args.espn_season, args.year)):
                    raise ValueError("Live mode needs ESPN/365Scores match IDs, --espn-season, --year and --scores365-season-id")
                if (args.sofascore_match_id is None) != (args.sofascore_season_id is None):
                    raise ValueError("Sofascore needs both native match and season IDs")
                selections = {"espn": {"identifier": args.espn_match_id, "year": args.espn_season, "season_id": None},
                              "scores365": {"identifier": args.scores365_match_id, "year": args.year, "season_id": args.scores365_season_id}}
                if args.sofascore_match_id is not None:
                    selections["sofascore"] = {"identifier": args.sofascore_match_id, "year": args.year, "season_id": args.sofascore_season_id}
                identities = read_identities((args.identities or DEFAULT_IDENTITIES).expanduser())
            cost = sum(COSTS[source] for source in selections)
            if args.max_match_requests is not None and args.max_match_requests < cost:
                raise ValueError(f"Selection requires {cost} endpoint reads, exceeding --max-match-requests")
            settings = default_settings(selections, allow_unknown_period=args.allow_unknown_period is True,
                                        minute_tolerance=args.minute_tolerance if args.minute_tolerance is not None else 1,
                                        tolerance_seconds=args.kickoff_tolerance if args.kickoff_tolerance is not None else 300)
            if args.demo:
                with workflow_directory("esd-champions-demo-") as temporary:
                    directory = args.cache_dir / "artificial-workflow" if args.cache_dir else temporary / "responses"

                    def artificial(url, **kwargs):
                        if url not in responses:
                            raise AssertionError(f"Unexpected artificial URL: {url}")
                        return deepcopy(responses[url])

                    with patch("esd._provider_datasets.get_api_json", side_effect=artificial) as fetch:
                        datasets = download(selections, directory, args.refresh, request_delay=0)
                        first_count = fetch.call_count
                        cached = download(selections, directory, False, request_delay=0)
                        assert fetch.call_count == first_count
                        assert all(first.metadata.response_fetched_at == second.metadata.response_fetched_at for first, second in zip(datasets, cached))
                    print("Artificial source data; cache reused", sum(len(item.metadata.cached_tasks) for item in cached), "tasks without HTTP")
            else:
                datasets = download(selections, args.cache_dir, args.refresh)
        reports = compare_sources(datasets, identities, settings)
        if args.parquet:
            with workflow_directory("esd-champions-roundtrip-") as temporary:
                directory = temporary / "workflow"
                save_bundle(directory, datasets, identities, settings, reports)
                restored = [esd.open_dataset(directory / source) for source in settings["sources"]]
                rules = json.loads((directory / "options.json").read_text(encoding="utf-8"))
                assert compare_sources(restored, read_identities(directory / "identities.json"), rules) == reports
                print("Temporary source snapshots and saved rules reproduce all comparisons")
        display(datasets, reports, args.limit, args.pandas)
        if args.output_dir is not None:
            save_bundle(args.output_dir, datasets, identities, settings, reports)
            print("Saved and verified:", args.output_dir)
        complete = all(dataset.complete and esd.validate_dataset(dataset).valid for dataset in datasets)
        linked = all(group["matches"] and not any((group["events"].linkage.unmatched_left, group["events"].linkage.unmatched_right,
                     group["events"].linkage.ambiguous_left, group["events"].linkage.ambiguous_right)) for group in reports.values())
        return 0 if complete and linked else 1
    except (ValueError, OSError, ImportError) as exc:
        parser.error(str(exc))
    except esd.ESDException as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

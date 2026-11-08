"""Bounded player and event downloads sharing match detail responses."""

from ._match_statistics import (
    _checked,
    _detail_options,
    _espn,
    _espn_match,
    _object,
    _scores,
    _scores_match,
    _sofa_event,
    _sofa_stats,
)
from .exceptions import SourceError
from .normalized.match_events import _event_key, normalize_match_events
from .normalized.match_players import MatchPlayerRecords, normalize_match_players


def _same_match(first, second):
    if (first.match_id, first.competition_id, first.home_team_id, first.away_team_id, first.kickoff) != (
        second.match_id, second.competition_id, second.home_team_id, second.away_team_id, second.kickoff,
    ):
        raise SourceError("Match statistics differ from the downloaded match context")


def load_match_players(**options):
    """Read explicit IDs only; shared responses count once against the budget."""
    from ._provider_datasets import _Download
    from .espn.endpoints import ESPNEndpoints
    from .scores365.endpoints import Scores365Endpoints
    from .sofascore.endpoints import SofascoreEndpoints

    source = options["source"]
    with_stats = "match_stats" in options["tables"]
    with_players = bool(set(options["tables"]) & {"lineups", "player_match_stats"})
    with_events = "match_events" in options["tables"]
    requests = (1 if source == "espn" else
                1 + int(with_stats) + (int(with_players) + int(with_events) if source == "sofascore" else 0))
    identifiers = _detail_options(options, requests_per_match=requests,
                                  allowed_tables=("matches", "teams", "match_stats", "lineups", "player_match_stats", "match_events"))
    download = _Download(options)
    download.requested_ids = identifiers
    if source == "espn":
        steps = ("match_details",)
    elif source == "sofascore":
        steps = ("match",) + (("lineups",) if with_players else ()) + (("match_events",) if with_events else ())
    else:
        steps = ("lineups" if with_players else "match_events",)
    if source != "espn" and with_stats:
        steps += ("match_stats",)
    for identifier in identifiers:
        for step in steps:
            download.expect(step, identifier)
    endpoints = (Scores365Endpoints(timezone_name="UTC") if source == "scores365" else
                 {"espn": ESPNEndpoints, "sofascore": SofascoreEndpoints}[source]())
    include_statistics = "player_match_stats" in options["tables"]

    def commit_players(result):
        match, players, statistics, events = result
        if source != "sofascore":
            download.add("matches", [match], "match_id")
        download.add("lineups", players.lineups, lambda row: (row.match_id, row.team_id, row.player_id))
        if include_statistics:
            download.add("player_match_stats", players.player_match_stats,
                         lambda row: (row.match_id, row.team_id, row.player_id))
        if statistics is not None:
            download.add("match_stats", [statistics], "match_id")
        if with_events:
            download.add("match_events", events, _event_key)

    for identifier in identifiers:
        if source == "espn":
            def parse(data, identifier=identifier):
                match, stats = _espn(data, options, identifier) if with_stats else (_espn_match(data, options, identifier), None)
                players = normalize_match_players(data, match=match, include_statistics=include_statistics) if with_players else MatchPlayerRecords()
                events = normalize_match_events(data, match=match) if with_events else ()
                return match, players, stats, events
            download.run("match_details", identifier, endpoints.summary(identifier, options["league"]),
                         _checked(parse), commit_players, download.policy.live_ttl)
            continue
        if source == "scores365":
            def parse(data, identifier=identifier):
                match = _scores_match({"games": [_object(data.get("game"), "365Scores game")]}, options, identifier)
                players = normalize_match_players(data, match=match, include_statistics=include_statistics) if with_players else MatchPlayerRecords()
                events = normalize_match_events(data, match=match) if with_events else ()
                return match, players, None, events
            result = download.run("lineups" if with_players else "match_events", identifier, endpoints.game_detail(int(identifier)),
                                  _checked(parse), commit_players, download.policy.live_ttl)
            context = result[0] if result is not None else None
            if with_stats:
                def parse_stats(data, identifier=identifier, context=context):
                    match, stats = _scores(data, options, identifier)
                    if context is not None:
                        _same_match(context, match)
                    return match, stats

                def commit_stats(result):
                    match, stats = result
                    download.add("matches", [match], "match_id")
                    download.add("match_stats", [stats], "match_id")
                download.run("match_stats", identifier, endpoints.game_stats(int(identifier)),
                             _checked(parse_stats), commit_stats, download.policy.live_ttl)
            continue
        context = download.run("match", identifier, endpoints.event_endpoint(int(identifier)),
                               _checked(lambda data, identifier=identifier: _sofa_event(data, options, identifier)),
                               lambda match: download.add("matches", [match], "match_id"), download.policy.live_ttl)
        if context is None:
            for step in steps[1:]:
                download.report(step, identifier, SourceError("Match details require verified event context"))
            continue
        if with_players:
            download.run("lineups", identifier, endpoints.match_lineups_endpoint(int(identifier)),
                         _checked(lambda data, context=context: (
                             context, normalize_match_players(data, match=context, include_statistics=include_statistics), None, (),
                         )), commit_players, download.policy.live_ttl)
        if with_events:
            download.run("match_events", identifier, endpoints.match_events_endpoint(int(identifier)),
                         _checked(lambda data, context=context: normalize_match_events(data, match=context)),
                         lambda rows: download.add("match_events", rows, _event_key), download.policy.live_ttl)
        if with_stats:
            download.run("match_stats", identifier, endpoints.match_stats_endpoint(int(identifier)),
                         _checked(lambda data, identifier=identifier: _sofa_stats(data, identifier)),
                         lambda row: download.add("match_stats", [row], "match_id"), download.policy.live_ttl)
    return download.snapshot()

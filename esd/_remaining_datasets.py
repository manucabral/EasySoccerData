"""Dataset plans for native seasons, dated pages and entity histories."""

from __future__ import annotations

import re
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from lxml import html

from .besoccer.endpoints import BeSoccerEndpoints
from .besoccer.types import parse_livescore_html, parse_standings_html
from .exceptions import SourceBlocked, SourceError
from .fbref.endpoints import FBrefEndpoints
from .fbref.types import parse_matchs
from .goaloo.endpoints import GoalooEndpoints
from .goaloo.types import parse_league, parse_matches, parse_standings, parse_teams
from .normalized import (
    NormalizedMarketValue,
    NormalizedMatchStats,
    NormalizedPlayer,
    NormalizedTransfer,
    normalize_match,
    normalize_standings,
    normalize_team,
)
from .promiedos.endpoints import PromiedosEndpoints
from .promiedos.service import _PROMIEDOS_HEADERS
from .promiedos.types import parse_events
from .transfermarkt.endpoints import TransfermarktEndpoints
from .transfermarkt.types import (
    parse_club,
    parse_market_value_history,
    parse_player,
    parse_transfer_history,
)
from .utils import get_api_json, get_text


def _selection_ids(value, name):
    if isinstance(value, (str, bytes)) or not value:
        raise ValueError(f"{name} requires a nonempty sequence of positive native IDs")
    if any(isinstance(item, bool) or not str(item).isdigit() or int(item) < 1 for item in value):
        raise ValueError(f"Invalid {name}")
    if len({str(item) for item in value}) != len(value):
        raise ValueError(f"Duplicate {name}")


def validate_options(opt):
    source, tables = opt["source"], opt["tables"]
    if (
        opt["anchor_date"] is not None
        or opt["match_ids"] is not None
        or opt["season_id"] is not None
        or opt["max_pages"] != 100
    ):
        raise ValueError(
            "This source does not support anchor_date, match_ids, season_id or max_pages"
        )
    if opt["source_timezone"] not in (None, "UTC"):
        ZoneInfo(opt["source_timezone"])
    if source in ("fbref", "goaloo") and (not opt["league"].isdigit() or int(opt["league"]) < 1):
        raise ValueError("A positive numeric native competition ID is required")
    if source == "goaloo":
        value = opt["source_season"]
        if not isinstance(value, str) or not re.fullmatch(r"\d{4}(?:-\d{4})?", value):
            raise ValueError("Goaloo requires explicit source_season, e.g. 2024-2025")
        if int(value[:4]) != opt["season"]:
            raise ValueError("source_season start year conflicts with season")
    elif opt["source_season"] is not None:
        raise ValueError("source_season is supported only for Goaloo")
    dated = source in ("fbref", "promiedos", "besoccer") and (
        "matches" in tables or "match_stats" in tables
    )
    if dated:
        if not opt["start_date"] or not opt["end_date"]:
            raise ValueError("This source requires explicit start_date and end_date")
        start, end = (
            datetime.strptime(opt[key], "%Y-%m-%d").date() for key in ("start_date", "end_date")
        )
        if any(
            value.isoformat() != opt[key]
            for key, value in (("start_date", start), ("end_date", end))
        ):
            raise ValueError("Dates must use YYYY-MM-DD")
        if not 0 <= (end - start).days <= 730:
            raise ValueError("Date range must be ordered and at most 731 days")
    elif opt["start_date"] is not None or opt["end_date"] is not None:
        raise ValueError("Date ranges require a dated match or match_stats selection")
    if source == "transfermarkt":
        if opt["source_timezone"] is not None:
            raise ValueError(
                "Transfermarkt retains native date strings; source_timezone is unsupported"
            )
        if "teams" in tables:
            _selection_ids(opt["club_ids"], "club_ids")
        elif opt["club_ids"] is not None:
            raise ValueError("club_ids requires teams")
        if any(table in tables for table in ("players", "market_values", "transfers")):
            _selection_ids(opt["player_ids"], "player_ids")
        elif opt["player_ids"] is not None:
            raise ValueError("player_ids requires players, market_values or transfers")
    elif opt["club_ids"] is not None or opt["player_ids"] is not None:
        raise ValueError("Entity selections are supported only for Transfermarkt")


def _ids(rows, field):
    if any(getattr(row, field) in (None, "", "0") for row in rows):
        raise SourceError(f"Source record is missing {field}")
    return rows


def _goaloo(download):
    opt = download.options
    url = GoalooEndpoints().data_endpoint(int(opt["league"]), opt["source_season"])

    def parse(data):
        if (
            not isinstance(data, dict)
            or not isinstance(data.get("LeagueInfo"), list)
            or not isinstance(data.get("TeamInfo"), list)
        ):
            raise SourceError("Goaloo response is missing league/team data")
        league = parse_league(data["LeagueInfo"])
        if str(league.id) != opt["league"] or league.season != opt["source_season"]:
            raise SourceError("Goaloo returned another competition or source season")
        teams = parse_teams(data["TeamInfo"])
        result = {}
        if "matches" in opt["tables"]:
            if not isinstance(data.get("ScheduleList"), dict):
                raise SourceError("Goaloo response is missing ScheduleList")
            for entries in data["ScheduleList"].values():
                if not isinstance(entries, list) or any(
                    not isinstance(row, list) or len(row) < 8 or str(row[1]) != opt["league"]
                    for row in entries
                ):
                    raise SourceError("Goaloo schedule has malformed rows or another competition")
            result["matches"] = _ids(
                [
                    replace(
                        normalize_match(
                            match,
                            competition_id=opt["league"],
                            season=opt["season"],
                            source_timezone=opt["source_timezone"],
                        ),
                        competition_name=league.name,
                        source_season_id=league.season,
                    )
                    for match in parse_matches(data["ScheduleList"], teams)
                ],
                "match_id",
            )
        if "teams" in opt["tables"]:
            result["teams"] = _ids([normalize_team(team) for team in teams.values()], "team_id")
        if "standings" in opt["tables"]:
            if not isinstance(data.get("TotalScore"), list) or any(
                not isinstance(row, list) or len(row) < 17 for row in data["TotalScore"]
            ):
                raise SourceError("Goaloo response is missing valid TotalScore rows")
            result["standings"] = _ids(
                [
                    replace(row, source_season_id=league.season, table_name="TotalScore")
                    for table in parse_standings(data["TotalScore"], teams)
                    for row in normalize_standings(
                        table, competition_id=opt["league"], season=opt["season"]
                    )
                ],
                "team_id",
            )
        return result

    def commit(batch):
        for table, rows in batch.items():
            download.add(table, rows, "match_id" if table == "matches" else "team_id")

    download.run(
        "season",
        opt["source_season"],
        url,
        parse,
        commit,
        min(download.policy.calendar_ttl, download.policy.standings_ttl, download.policy.live_ttl),
    )


def _document(data):
    if (
        not isinstance(data, dict)
        or not isinstance(data.get("html"), str)
        or not data["html"].strip()
    ):
        raise SourceError("Source returned no HTML")
    text = data["html"]
    if any(
        marker in text[:4000].lower() for marker in ("client challenge", "just a moment", "cf-chl-")
    ):
        raise SourceBlocked("Source returned a browser challenge")
    doc = html.fromstring(text)
    for comment in doc.xpath("//comment()"):
        if "<table" in (comment.text or ""):
            comment.addprevious(html.fragment_fromstring(comment.text, create_parent="div"))
    return doc


def _fbref(data, opt, day):
    doc = _document(data)
    tables = doc.xpath("//table[starts-with(@id, 'sched')]")
    if not tables:
        raise SourceError("FBref page has no schedule tables")
    result = []
    for table in tables:
        context = table.xpath(
            ".//caption//a/@href | ./ancestor::div[1]/div[contains(@class, 'section_heading')]//a/@href"
        )
        competitions = {m.group(1) for href in context if (m := re.search(r"/comps/(\d+)", href))}
        wrapper = html.Element("div")
        wrapper.append(table)
        for model in parse_matchs(wrapper):
            competition = model.competition_id
            if competition is None and len(competitions) == 1:
                competition = next(iter(competitions))
            if competition is None:
                raise SourceError("FBref schedule row has no identifiable competition")
            if competition != opt["league"]:
                continue
            if model.date is not None and model.date != day:
                raise SourceError("FBref returned another match date")
            model = replace(model, date=model.date or day, competition_id=competition)
            record = normalize_match(
                model,
                competition_id=opt["league"],
                season=opt["season"],
                source_timezone=opt["source_timezone"],
            )
            # stathead links are comparisons, not stable match identities.
            if model.id_type != "matches" or not record.match_id:
                raise SourceError("FBref fixture has no native match report ID")
            result.append(record)
    return result


def _fbref_stats(data, rows):
    doc = _document(data)
    raw = {}
    selected = {row.match_id for row in rows}
    for tr in doc.xpath("//table[starts-with(@id, 'sched')]//tbody/tr"):
        for href in tr.xpath(".//*[@data-stat='match_report']//a/@href"):
            found = re.search(r"/matches/([^/?]+)", href)
            if found and found.group(1) in selected:

                def value(name, tr=tr):
                    texts = tr.xpath(f".//*[@data-stat='{name}']/text()")
                    return float(texts[0].strip()) if texts and texts[0].strip() else None

                raw[found.group(1)] = (value("home_xg"), value("away_xg"))
    return [
        NormalizedMatchStats("fbref", row.match_id, *raw.get(row.match_id, (None, None)))
        for row in rows
    ]


def _promiedos(data, opt, day):
    if not isinstance(data, dict) or not isinstance(data.get("leagues"), list):
        raise SourceError("Promiedos response is missing leagues")
    selected = [league for league in data["leagues"] if str(league.get("id")) == opt["league"]]
    if any(not isinstance(league.get("games"), list) for league in selected):
        raise SourceError("Promiedos response is missing games")
    result = []
    for event in parse_events(day, selected):
        for model in event.matches:
            if (
                model.raw_start_time
                and datetime.strptime(model.raw_start_time, "%d-%m-%Y %H:%M").date().isoformat()
                != day
            ):
                raise SourceError("Promiedos returned another match date")
            model.league = event.league
            result.append(
                normalize_match(
                    model,
                    competition_id=opt["league"],
                    season=opt["season"],
                    source_timezone=opt["source_timezone"],
                )
            )
    return _ids(result, "match_id")


def _besoccer(data, opt, day):
    doc = _document(data)
    for canonical in doc.xpath("//link[@rel='canonical']/@href"):
        if "/livescore/" in canonical and canonical.rstrip("/").rsplit("/", 1)[-1] != day:
            raise SourceError("BeSoccer returned another canonical date page")
    if not doc.xpath("//a[starts-with(@id, 'match-')] | //a[@data-cy='competitionName']"):
        raise SourceError("BeSoccer page has no recognizable match listing")
    models = [
        match
        for match in parse_livescore_html(data["html"])
        if match.competition_slug == opt["league"]
    ]
    records = [
        normalize_match(
            model,
            competition_id=opt["league"],
            season=opt["season"],
            source_timezone=opt["source_timezone"],
        )
        for model in models
    ]
    zone = (
        timezone.utc
        if opt["source_timezone"] in (None, "UTC")
        else ZoneInfo(opt["source_timezone"])
    )
    # The source page also includes adjacent-day fixtures. Filter them locally.
    return _ids(
        [
            row
            for row in records
            if row.kickoff is None or row.kickoff.astimezone(zone).date().isoformat() == day
        ],
        "match_id",
    )


def _dated(download):
    opt, source = download.options, download.options["source"]
    if source in ("fbref", "besoccer"):

        def fetch(url):
            return {"html": get_text(url, proxies=opt["proxies"], impersonate="chrome")}

        download.reader.fetch = fetch
    else:
        download.reader.fetch = lambda url: get_api_json(
            url, proxies=opt["proxies"], headers=_PROMIEDOS_HEADERS
        )
    if source == "fbref":
        # Preserve the client's rate cap even when the user asks for no delay.
        download.reader.request_delay = max(opt["request_delay"], 60 / 9, 3.0)
    dates = []
    if "matches" in opt["tables"] or "match_stats" in opt["tables"]:
        start, end = (
            datetime.strptime(opt[key], "%Y-%m-%d").date() for key in ("start_date", "end_date")
        )
        dates = [
            (start + timedelta(days=offset)).isoformat() for offset in range((end - start).days + 1)
        ]
    for day in dates:
        download.expect("matches", day)
    if "standings" in opt["tables"]:
        download.expect("standings", str(opt["season"]))
    for day in dates:
        if source == "fbref":
            url = FBrefEndpoints().matchs_endpoint.format(date=day)
        elif source == "promiedos":
            url = PromiedosEndpoints().events_endpoint.format(date=day)
        else:
            url = BeSoccerEndpoints().livescore(day)

        def parse(data, day=day):
            rows = {"fbref": _fbref, "promiedos": _promiedos, "besoccer": _besoccer}[source](
                data, opt, day
            )
            stats = _fbref_stats(data, rows) if "match_stats" in opt["tables"] else []
            return rows, stats

        def commit(batch):
            rows, stats = batch
            if "matches" in opt["tables"]:
                download.add("matches", rows, "match_id")
            if "match_stats" in opt["tables"]:
                download.add("match_stats", stats, "match_id")

        download.run(
            "matches",
            day,
            url,
            parse,
            commit,
            min(download.policy.calendar_ttl, download.policy.live_ttl),
        )
    if "standings" in opt["tables"]:

        def parse(data):
            doc = _document(data)
            if not doc.xpath(
                "//tr[contains(concat(' ', normalize-space(@class), ' '), ' row-body ')]"
            ):
                raise SourceError("BeSoccer standings page has no recognizable standings rows")
            return _ids(
                [
                    row
                    for model in parse_standings_html(data["html"])
                    for row in normalize_standings(
                        model, competition_id=opt["league"], season=opt["season"]
                    )
                ],
                "team_id",
            )

        download.run(
            "standings",
            str(opt["season"]),
            BeSoccerEndpoints().standings(opt["league"], opt["season"]),
            parse,
            lambda rows: download.add("standings", rows, "team_id"),
            download.policy.standings_ttl,
        )


def _transfermarkt(download):
    opt, endpoints = download.options, TransfermarktEndpoints()
    for club in opt["club_ids"] or ():
        download.expect("teams", str(club))
    for player in opt["player_ids"] or ():
        for table in ("players", "market_values", "transfers"):
            if table in opt["tables"]:
                download.expect(table, str(player))
    for club in opt["club_ids"] or ():

        def parse(data, club=club):
            model = parse_club(data)
            if model.id != str(club) or model.competition_id != opt["league"]:
                raise SourceError(
                    "Transfermarkt club ID or competition does not match the selection"
                )
            return [normalize_team(model)]

        download.run(
            "teams",
            str(club),
            endpoints.club_profile(club),
            parse,
            lambda rows: download.add("teams", rows, "team_id"),
        )
    for player in opt["player_ids"] or ():
        if "players" in opt["tables"]:

            def parse(data, player=player):
                model = parse_player(data)
                if model.id != str(player):
                    raise SourceError("Transfermarkt returned another player")
                return [
                    NormalizedPlayer(
                        "transfermarkt",
                        model.id,
                        model.name,
                        str(model.current_club_id) if model.current_club_id is not None else None,
                        model.position,
                        model.date_of_birth,
                        model.market_value,
                        model.market_value_currency,
                    )
                ]

            download.run(
                "players",
                str(player),
                endpoints.player_profile(player),
                parse,
                lambda rows: download.add("players", rows, "player_id"),
            )
        for table in ("market_values", "transfers"):
            if table not in opt["tables"]:
                continue

            def parse(data, player=player, table=table):
                if not isinstance(data, dict):
                    raise SourceError("Transfermarkt history is not an object")
                body = data.get("data", data)
                history = body.get("history") if isinstance(body, dict) else None
                if table == "market_values":
                    if not isinstance(history, list):
                        raise SourceError("Transfermarkt valuation history is missing")
                    models = parse_market_value_history(data)
                    if any(model.player_id != str(player) for model in models):
                        raise SourceError("Transfermarkt valuations belong to another player")
                    return [
                        NormalizedMarketValue(
                            "transfermarkt",
                            model.player_id,
                            model.club_id,
                            str(model.season_id) if model.season_id is not None else None,
                            model.date,
                            model.value,
                            model.currency,
                        )
                        for model in models
                    ]
                if not isinstance(history, dict) or any(
                    not isinstance(history.get(key), list) for key in ("pending", "terminated")
                ):
                    raise SourceError(
                        "Transfermarkt transfer history is missing pending/terminated lists"
                    )
                models = parse_transfer_history(data)
                if any(model.player_id != str(player) for model in models):
                    raise SourceError("Transfermarkt transfers belong to another player")
                return _ids(
                    [
                        NormalizedTransfer(
                            "transfermarkt",
                            model.id,
                            model.player_id,
                            model.season,
                            model.date,
                            model.from_club_id,
                            model.to_club_id,
                            model.fee,
                            model.fee_display,
                            str(model.is_pending).lower(),
                            model.transfer_type,
                        )
                        for model in models
                    ],
                    "transfer_id",
                )

            endpoint = (
                endpoints.player_market_value_history
                if table == "market_values"
                else endpoints.player_transfer_history
            )
            key = (
                (lambda row: (row.player_id, row.source_date, row.team_id, row.source_season_id))
                if table == "market_values"
                else "transfer_id"
            )
            download.run(
                table,
                str(player),
                endpoint(player),
                parse,
                lambda rows, table=table, key=key: download.add(table, rows, key),
            )


def load_remaining(download):
    source = download.options["source"]
    if source == "goaloo":
        _goaloo(download)
    elif source == "transfermarkt":
        _transfermarkt(download)
    else:
        _dated(download)

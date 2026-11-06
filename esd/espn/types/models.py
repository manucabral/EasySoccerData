"""
ESPN dataclasses and parsers.
"""

from __future__ import annotations

from dataclasses import dataclass, field


def _to_int(val, default: int | None = 0) -> int | None:
    try:
        return int(float(val)) if val is not None else default
    except (ValueError, TypeError):
        return default


@dataclass
class ESPNTeam:
    """
    A soccer club or national team in ESPN.
    """

    id: str = None
    name: str = None
    short_name: str = None
    abbreviation: str = None
    color: str = None
    alternate_color: str = None
    logo_url: str = None
    score: int | None = None
    winner: bool = False
    form: str = None


@dataclass
class ESPNStatItem:
    """
    A team statistic entry from an ESPN match boxscore.
    """

    name: str = None
    label: str = None
    value: str = None


@dataclass
class ESPNRosterPlayer:
    """
    A player in an ESPN match roster.
    """

    id: str = None
    full_name: str = None
    short_name: str = None
    jersey: str = None
    position: str = None
    position_abbr: str = None
    starter: bool = False
    subbed_in: bool = False
    subbed_out: bool = False


@dataclass
class ESPNKeyEvent:
    """
    A timeline incident (goal, card, substitution, kickoff) in an ESPN match.
    """

    id: str = None
    event_type: str = None
    type_text: str = None
    text: str = None
    period: int = 1
    clock_value: float = 0.0
    clock_display: str = None
    scoring_play: bool = False
    team_id: str = None


@dataclass
class ESPNMatch:
    """
    A match from the ESPN scoreboard.
    """

    id: str = None
    name: str = None
    short_name: str = None
    date: str = None
    status_name: str = None
    status_state: str = None
    status_detail: str = None
    completed: bool = False
    venue_name: str = None
    venue_city: str = None
    attendance: int = 0
    home_team: ESPNTeam = field(default_factory=ESPNTeam)
    away_team: ESPNTeam = field(default_factory=ESPNTeam)


@dataclass
class ESPNMatchSummary:
    """
    Detailed match summary including stats, rosters and timeline events.
    """

    event_id: str = None
    venue_name: str = None
    attendance: int = 0
    home_team: ESPNTeam = field(default_factory=ESPNTeam)
    away_team: ESPNTeam = field(default_factory=ESPNTeam)
    home_stats: list[ESPNStatItem] = field(default_factory=list)
    away_stats: list[ESPNStatItem] = field(default_factory=list)
    home_roster: list[ESPNRosterPlayer] = field(default_factory=list)
    away_roster: list[ESPNRosterPlayer] = field(default_factory=list)
    key_events: list[ESPNKeyEvent] = field(default_factory=list)
    commentary: list[str] = field(default_factory=list)


@dataclass
class ESPNStandingRow:
    """
    A single row in an ESPN league standings table.
    """

    rank: int = 0
    team: ESPNTeam = field(default_factory=ESPNTeam)
    played: int = 0
    won: int = 0
    drawn: int = 0
    lost: int = 0
    goals_for: int = 0
    goals_against: int = 0
    goal_diff: int = 0
    points: int = 0
    deductions: int = 0


@dataclass
class ESPNStandingTable:
    """
    A stage or group standings table in ESPN.
    """

    id: str = None
    name: str = None
    abbreviation: str = None
    rows: list[ESPNStandingRow] = field(default_factory=list)


def _parse_team_obj(team_dict: dict, comp_dict: dict | None = None) -> ESPNTeam:
    if not team_dict:
        return ESPNTeam()
    logos = team_dict.get("logos") or []
    logo_url = team_dict.get("logo") or (logos[0].get("href") if logos else None)
    raw_score = comp_dict.get("score") if comp_dict else None
    return ESPNTeam(
        id=str(team_dict.get("id")) if team_dict.get("id") is not None else None,
        name=team_dict.get("displayName") or team_dict.get("name"),
        short_name=team_dict.get("shortDisplayName") or team_dict.get("name"),
        abbreviation=team_dict.get("abbreviation"),
        color=team_dict.get("color"),
        alternate_color=team_dict.get("alternateColor"),
        logo_url=logo_url,
        score=_to_int(raw_score, None) if raw_score is not None else None,
        winner=bool(comp_dict.get("winner", False)) if comp_dict else False,
        form=comp_dict.get("form") if comp_dict else None,
    )


def parse_scoreboard(data: dict) -> list[ESPNMatch]:
    """
    Parse matches from an ESPN scoreboard payload.
    """
    if not data:
        return []
    matches: list[ESPNMatch] = []
    for ev in data.get("events", []) or []:
        comps = ev.get("competitions") or []
        comp = comps[0] if comps else {}
        status_type = (ev.get("status") or comp.get("status") or {}).get("type") or {}
        venue = comp.get("venue") or {}
        address = venue.get("address") or {}
        home = ESPNTeam()
        away = ESPNTeam()
        for c in comp.get("competitors", []) or []:
            parsed = _parse_team_obj(c.get("team") or {}, c)
            if c.get("homeAway") == "home":
                home = parsed
            else:
                away = parsed
        matches.append(
            ESPNMatch(
                id=str(ev.get("id")) if ev.get("id") is not None else None,
                name=ev.get("name"),
                short_name=ev.get("shortName"),
                date=ev.get("date"),
                status_name=status_type.get("name"),
                status_state=status_type.get("state"),
                status_detail=status_type.get("shortDetail")
                or status_type.get("detail"),
                completed=bool(status_type.get("completed", False)),
                venue_name=venue.get("fullName"),
                venue_city=address.get("city"),
                attendance=_to_int(comp.get("attendance"), 0),
                home_team=home,
                away_team=away,
            )
        )
    return matches


def _parse_roster_list(roster_entries: list[dict]) -> list[ESPNRosterPlayer]:
    players: list[ESPNRosterPlayer] = []
    for item in roster_entries or []:
        ath = item.get("athlete") or {}
        pos = item.get("position") or {}
        players.append(
            ESPNRosterPlayer(
                id=str(ath.get("id")) if ath.get("id") is not None else None,
                full_name=ath.get("fullName") or ath.get("displayName"),
                short_name=ath.get("shortName") or ath.get("displayName"),
                jersey=str(item.get("jersey"))
                if item.get("jersey") is not None
                else None,
                position=pos.get("displayName") or pos.get("name"),
                position_abbr=pos.get("abbreviation"),
                starter=bool(item.get("starter", False)),
                subbed_in=bool(item.get("subbedIn", False)),
                subbed_out=bool(item.get("subbedOut", False)),
            )
        )
    return players


def parse_summary(data: dict) -> ESPNMatchSummary:
    """
    Parse an ESPN match summary payload.
    """
    if not data:
        return ESPNMatchSummary()
    header = data.get("header") or {}
    h_comps = header.get("competitions") or []
    h_comp = h_comps[0] if h_comps else {}
    home_team = ESPNTeam()
    away_team = ESPNTeam()
    for c in h_comp.get("competitors", []) or []:
        parsed = _parse_team_obj(c.get("team") or {}, c)
        if c.get("homeAway") == "home":
            home_team = parsed
        else:
            away_team = parsed

    box = data.get("boxscore") or {}
    box_teams = box.get("teams") or []
    home_stats: list[ESPNStatItem] = []
    away_stats: list[ESPNStatItem] = []
    for idx, bt in enumerate(box_teams):
        t_id = str((bt.get("team") or {}).get("id") or "")
        stats = [
            ESPNStatItem(
                name=s.get("name"),
                label=s.get("label"),
                value=str(s.get("displayValue", "")),
            )
            for s in (bt.get("statistics") or [])
        ]
        if (home_team.id and t_id == home_team.id) or idx == 0:
            home_stats = stats
        else:
            away_stats = stats

    home_roster: list[ESPNRosterPlayer] = []
    away_roster: list[ESPNRosterPlayer] = []
    for idx, r_group in enumerate(data.get("rosters") or []):
        roster_list = _parse_roster_list(r_group.get("roster") or [])
        if r_group.get("homeAway") == "home" or idx == 0:
            home_roster = roster_list
        else:
            away_roster = roster_list

    key_events: list[ESPNKeyEvent] = []
    for kev in data.get("keyEvents") or []:
        ev_type = kev.get("type") or {}
        clock = kev.get("clock") or {}
        period = kev.get("period") or {}
        team_obj = kev.get("team") or {}
        key_events.append(
            ESPNKeyEvent(
                id=str(kev.get("id")) if kev.get("id") is not None else None,
                event_type=ev_type.get("type"),
                type_text=ev_type.get("text"),
                text=kev.get("text"),
                period=_to_int(period.get("number"), 1),
                clock_value=float(clock.get("value", 0.0) or 0.0),
                clock_display=clock.get("displayValue"),
                scoring_play=bool(kev.get("scoringPlay", False)),
                team_id=str(team_obj.get("id"))
                if team_obj.get("id") is not None
                else None,
            )
        )

    commentary = [
        c.get("text")
        for c in (data.get("commentary") or [])
        if isinstance(c, dict) and c.get("text")
    ]
    g_info = data.get("gameInfo") or {}
    venue = g_info.get("venue") or {}
    return ESPNMatchSummary(
        event_id=str(header.get("id")) if header.get("id") is not None else None,
        venue_name=venue.get("fullName"),
        attendance=_to_int(g_info.get("attendance"), 0),
        home_team=home_team,
        away_team=away_team,
        home_stats=home_stats,
        away_stats=away_stats,
        home_roster=home_roster,
        away_roster=away_roster,
        key_events=key_events,
        commentary=commentary,
    )


def parse_standings(data: dict) -> list[ESPNStandingTable]:
    """
    Parse league standings tables from an ESPN standings payload.
    """
    if not data:
        return []
    children = data.get("children")
    groups = children if children else ([data] if "standings" in data else [])
    tables: list[ESPNStandingTable] = []
    for grp in groups:
        st = grp.get("standings") or {}
        rows: list[ESPNStandingRow] = []
        for entry in st.get("entries") or []:
            stat_map = {
                s.get("name"): s.get("value")
                for s in (entry.get("stats") or [])
                if "name" in s
            }
            rows.append(
                ESPNStandingRow(
                    rank=_to_int(stat_map.get("rank"), 0),
                    team=_parse_team_obj(entry.get("team") or {}),
                    played=_to_int(stat_map.get("gamesPlayed"), 0),
                    won=_to_int(stat_map.get("wins"), 0),
                    drawn=_to_int(stat_map.get("ties"), 0),
                    lost=_to_int(stat_map.get("losses"), 0),
                    goals_for=_to_int(stat_map.get("pointsFor"), 0),
                    goals_against=_to_int(stat_map.get("pointsAgainst"), 0),
                    goal_diff=_to_int(stat_map.get("pointDifferential"), 0),
                    points=_to_int(stat_map.get("points"), 0),
                    deductions=_to_int(stat_map.get("deductions"), 0),
                )
            )
        tables.append(
            ESPNStandingTable(
                id=str(grp.get("id")) if grp.get("id") is not None else None,
                name=grp.get("name") or st.get("displayName"),
                abbreviation=grp.get("abbreviation"),
                rows=rows,
            )
        )
    return tables


def parse_teams(data: dict) -> list[ESPNTeam]:
    """
    Parse club list from an ESPN league teams payload.
    """
    if not data:
        return []
    teams: list[ESPNTeam] = []
    for sport in data.get("sports", []) or []:
        for lg in sport.get("leagues", []) or []:
            for wrapper in lg.get("teams", []) or []:
                t = wrapper.get("team") or wrapper
                teams.append(_parse_team_obj(t))
    return teams

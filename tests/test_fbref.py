"""Tests for esd.fbref parsers and service validation."""

import pytest
from lxml import html

from esd.fbref.exceptions import InvalidMatchId
from esd.fbref.service import FBrefService
from esd.fbref.types import parse_league_players, parse_match_details, parse_matchs


def test_parse_matchs_strips_any_language_prefix():
    doc = html.fromstring(
        """
        <html><body>
        <table id="sched_2026_9">
            <tbody>
                <tr class="thead"><th>Round</th></tr>
                <tr>
                    <td data-stat="round">Matchweek 1</td>
                    <td data-stat="home_team"><a href="/pt-br/squads/1">Arsenal</a></td>
                    <td data-stat="home_xg">1.8</td>
                    <td data-stat="score"><a href="/pt-br/matches/abc123/Report">2–1</a></td>
                    <td data-stat="away_xg">0.9</td>
                    <td data-stat="away_team"><a href="/pt-br/squads/2">Chelsea</a></td>
                    <td data-stat="match_report"><a href="/pt-br/matches/abc123/Report">Match Report</a></td>
                </tr>
            </tbody>
        </table>
        </body></html>
        """
    )
    matches = parse_matchs(doc)
    assert len(matches) == 1
    assert matches[0].id == "/matches/abc123/Report"
    assert matches[0].id_type == "matches"
    assert matches[0].home_score == 2
    assert matches[0].away_score == 1
    assert matches[0].home_xg == 1.8


def test_parse_league_players_from_html_comment():
    doc = html.fromstring(
        """
        <html><body>
        <div id="all_stats_standard">
        <!--
        <table id="stats_standard">
            <tbody>
                <tr class="thead"><th>Player</th></tr>
                <tr>
                    <th data-stat="ranker">1</th>
                    <td data-stat="player"><a href="/en/players/p1">Erling Haaland</a></td>
                    <td data-stat="nationality">no NOR</td>
                    <td data-stat="position">FW</td>
                    <td data-stat="team">Manchester City</td>
                    <td data-stat="games">31</td>
                    <td data-stat="minutes">2,700</td>
                    <td data-stat="goals">27</td>
                    <td data-stat="xg">24.1</td>
                </tr>
            </tbody>
        </table>
        -->
        </div>
        </body></html>
        """
    )
    players = parse_league_players(doc, table_id="stats_standard")
    assert len(players) == 1
    assert players[0].player == "Erling Haaland"
    assert players[0].nationality == "NOR"
    assert players[0].minutes == 2700
    assert players[0].goals == 27
    assert players[0].xg == 24.1


def test_parse_match_details_switcher_and_types():
    doc = html.fromstring(
        """
        <html><body>
        <div id="switcher_player_stats_home">
            <table>
                <tbody>
                    <tr class="thead"><th>Header</th></tr>
                    <tr>
                        <th></th>
                        <th data-stat="player">Bukayo Saka</th>
                        <td data-stat="minutes">90</td>
                        <td data-stat="goals">1</td>
                        <td data-stat="xg">0.85</td>
                    </tr>
                </tbody>
            </table>
        </div>
        <div id="switcher_player_stats_away">
            <table>
                <tbody>
                    <tr>
                        <th data-stat="player">Cole Palmer</th>
                        <td data-stat="minutes">90</td>
                        <td data-stat="goals">1</td>
                        <td data-stat="xg">0.70</td>
                    </tr>
                </tbody>
            </table>
        </div>
        <table id="keeper_stats_home">
            <caption>Home Keeper</caption>
            <tbody>
                <tr>
                    <th data-stat="player">David Raya</th>
                    <td data-stat="minutes">90</td>
                    <td data-stat="gk_saves">4</td>
                    <td data-stat="gk_save_pct">80.0</td>
                </tr>
            </tbody>
        </table>
        </body></html>
        """
    )
    details = parse_match_details(doc)
    assert len(details.home_players.summary) == 1
    assert details.home_players.summary[0].player == "Bukayo Saka"
    assert details.home_players.summary[0].minutes == 90
    assert details.home_players.summary[0].goals == 1
    assert details.home_players.summary[0].xg == 0.85
    assert len(details.away_players.summary) == 1
    assert details.away_players.summary[0].player == "Cole Palmer"
    assert len(details.home_keeper.rows) == 1
    assert details.home_keeper.rows[0].player == "David Raya"
    assert details.home_keeper.rows[0].gk_saves == 4
    assert details.home_keeper.rows[0].gk_save_pct == 80.0


def test_get_match_details_invalid_id_does_not_hit_network():
    service = FBrefService(use_curl_cffi=False, use_playwright=False)
    with pytest.raises(InvalidMatchId):
        service.get_match_details("invalid-id")

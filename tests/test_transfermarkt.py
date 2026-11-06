"""
Unit tests for Transfermarkt parsers.
"""

from esd.transfermarkt.types import (
    parse_club,
    parse_market_value_history,
    parse_player,
    parse_search_html,
    parse_transfer_history,
)


def test_parse_transfermarkt_player_and_club():
    player = parse_player(
        {
            "data": {
                "id": "28003",
                "name": "Lionel Messi",
                "lifeDates": {"age": 38, "dateOfBirth": "1987-06-24"},
                "nationalityDetails": {"passportName": "Lionel Andrés Messi"},
                "attributes": {
                    "height": 1.7,
                    "contractUntil": "2028-12-31",
                    "preferredFoot": {"name": "left"},
                    "position": {"name": "Right Winger", "shortName": "RW"},
                    "positionGroupName": "Striker",
                },
                "marketValueDetails": {
                    "current": {
                        "value": 15000000,
                        "currency": "EUR",
                        "compact": {"prefix": "€", "content": "15.00", "suffix": "M"},
                    },
                    "highest": {"value": 180000000, "determined": "2018-05-30"},
                },
                "clubAssignments": [
                    {
                        "clubId": "69261",
                        "shirtNumber": 10,
                        "isCaptain": True,
                        "type": "current",
                    }
                ],
            }
        }
    )
    assert player.id == "28003"
    assert player.name == "Lionel Messi"
    assert player.market_value == 15000000
    assert player.market_value_display == "€15.00M"
    assert player.is_captain is True

    club = parse_club(
        {
            "data": {
                "id": "281",
                "name": "Manchester City",
                "baseDetails": {
                    "shortName": "Man City",
                    "abbreviation": "MCI",
                    "countryId": 189,
                    "primaryCompetitionId": "GB1",
                    "superiorClub": {
                        "location": {"street": "Etihad Stadium", "city": "Manchester"},
                        "colors": {"firstColor": "#84BBFF", "secondColor": "#FFFFFF"},
                    },
                },
                "squadDetails": {
                    "squadSize": 24,
                    "averageAge": 25.6,
                    "currentMarketValue": {
                        "value": 1498300000,
                        "compact": {"prefix": "€", "content": "1.50", "suffix": "B"},
                    },
                },
            }
        }
    )
    assert club.name == "Manchester City"
    assert club.current_market_value_display == "€1.50B"
    assert club.squad_size == 24


def test_parse_transfermarkt_histories_and_search():
    mv = parse_market_value_history(
        {
            "data": {
                "history": [
                    {
                        "playerId": "28003",
                        "clubId": "131",
                        "seasonId": 2018,
                        "age": 30,
                        "marketValue": {
                            "value": 180000000,
                            "currency": "EUR",
                            "determined": "2018-05-30",
                            "compact": {
                                "prefix": "€",
                                "content": "180.00",
                                "suffix": "M",
                            },
                        },
                    }
                ]
            }
        }
    )
    assert len(mv) == 1
    assert mv[0].value == 180000000

    transfers = parse_transfer_history(
        {
            "data": {
                "history": {
                    "terminated": [
                        {
                            "id": "4418847",
                            "transferSource": {"clubId": "583", "competitionId": "FR1"},
                            "transferDestination": {
                                "clubId": "69261",
                                "competitionId": "MLS1",
                            },
                            "details": {
                                "playerId": "28003",
                                "date": "2023-07-15",
                                "age": 36,
                                "isPending": False,
                                "season": {"display": "23/24"},
                                "marketValue": {
                                    "value": 35000000,
                                    "compact": {
                                        "prefix": "€",
                                        "content": "35.00",
                                        "suffix": "M",
                                    },
                                },
                                "fee": {
                                    "value": None,
                                    "compact": {
                                        "prefix": "",
                                        "content": "Free Transfer",
                                        "suffix": "",
                                    },
                                },
                            },
                            "typeDetails": {"type": "STANDARD"},
                        }
                    ]
                }
            }
        }
    )
    assert len(transfers) == 1
    assert transfers[0].fee_display == "Free Transfer"

    search_html = """
    <table>
      <tr>
        <td class="hauptlink">
          <a href="/julian-alvarez/profil/spieler/576024">Julián Álvarez</a>
        </td>
      </tr>
      <tr>
        <td class="hauptlink">
          <a href="/river-plate/startseite/verein/209">CA River Plate</a>
        </td>
      </tr>
    </table>
    """
    items = parse_search_html(search_html)
    assert len(items) == 2
    assert items[0].entity_type == "player"
    assert items[0].id == "576024"
    assert items[1].entity_type == "club"
    assert items[1].id == "209"

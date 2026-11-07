"""Sofascore player profiles and parser."""

from dataclasses import dataclass, field

from .country import Country, parse_country
from .player_attributes import PlayerAttributes
from .team import Team, parse_team
from .transfer import TransferHistory


@dataclass
class Player:
    """A Sofascore player profile with position, contract and transfer information."""

    id: int = field(default=0)
    """
    Sofascore player ID, accepted by player detail methods.
    """
    name: str = field(default=None)
    """
    Player name reported by Sofascore.
    """
    slug: str = field(default=None)
    """
    The player slug.
    """
    short_name: str = field(default=None)
    """
    The player short name.
    """
    position: str = field(default=None)
    """
    The player position.
    """
    jersey_number: str = field(default=None)
    """
    The player jersey number.
    """
    height: int = field(default=0)
    """
    Height in centimetres.
    """
    preferred_foot: str = field(default=None)
    """
    The player preferred foot.
    """
    gender: str = field(default=None)
    """
    Source gender code, such as M or F.
    """
    shirt_number: int = field(default=0)
    """
    The player shirt number.
    """
    date_of_birth: int = field(default=0)
    """
    Birth date as a Unix timestamp.
    """
    contract_until: int = field(default=0)
    """
    Contract end date as a Unix timestamp.
    """
    market_value: int = field(default=0)
    """
    Source-proposed market value.
    """
    attributes: PlayerAttributes = field(default=None)
    """
    Attribute ratings and yearly overviews.
    """
    team: Team = field(default=None)
    """
    Current team reported by Sofascore.
    """
    country: Country = field(default=None)
    """
    The player country.
    """
    transfer_history: TransferHistory = field(default=None)


def parse_player(data: dict) -> Player:
    """
    Parse player data.

    Args:
        data (dict): Player data.

    Returns:
        Player: Player dataclass.
    """
    return Player(
        name=data.get("name", None),
        slug=data.get("slug", None),
        short_name=data.get("shortName", None),
        position=data.get("position", None),
        jersey_number=data.get("jerseyNumber", None),
        height=data.get("height", 0),
        preferred_foot=data.get("preferredFoot", None),
        gender=data.get("gender", None),
        id=data.get("id", 0),
        shirt_number=data.get("shirtNumber", 0),
        date_of_birth=data.get("dateOfBirthTimestamp", 0),
        contract_until=data.get("contractUntilTimestamp", 0),
        market_value=data.get("proposedMarketValue")
        or (data.get("proposedMarketValueRaw") or {}).get("value", 0),
        team=parse_team(data.get("team", {})),
        country=parse_country(data.get("country", {})),
    )

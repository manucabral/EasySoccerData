"""
Transfer history data classes.
"""

from dataclasses import dataclass, field

from .team import Team, parse_team


@dataclass
class TransferFeeRaw:
    """
    Represents the raw transfer fee data.
    """

    value: int = field(default=0)
    currency: str = field(default=None)


@dataclass
class TransferHistoryEntry:
    """
    Represents a single transfer record.
    """

    id: int = field(default=0)
    transfer_date_timestamp: int = field(default=0)
    type: int = field(default=0)
    transfer_fee: int = field(default=0)
    transfer_fee_description: str = field(default=None)
    from_team_name: str = field(default=None)
    to_team_name: str = field(default=None)
    transfer_fee_raw: TransferFeeRaw = field(default=None)
    transfer_from: Team = field(default=None)
    transfer_to: Team = field(default=None)


@dataclass
class TransferHistory:
    """
    Container for transfer history entries.
    """

    entries: list[TransferHistoryEntry] = field(default_factory=list)


def parse_transfer_fee_raw(data: dict) -> TransferFeeRaw:
    """
    Parse the raw fee data.
    """
    return TransferFeeRaw(
        value=data.get("value", 0), currency=data.get("currency", None)
    )


def strip_keys(src: dict, ignore: list) -> dict:
    """
    Return new dict omitting any keys in ignore list.
    """
    return {k: v for k, v in src.items() if k not in ignore}


def parse_transfer_history(data: dict) -> TransferHistory:
    """
    Parse a transfer history JSON into TransferHistory dataclass.

    Args:
        data (dict): JSON with a top-level "transferHistory" key.
    Returns:
        TransferHistory: Parsed history.
    """
    history = TransferHistory()
    for item in data.get("transferHistory", []):
        raw_from = strip_keys(
            item.get("transferFrom", {}), ["sport", "fieldTranslations"]
        )
        raw_to = strip_keys(item.get("transferTo", {}), ["sport", "fieldTranslations"])

        entry = TransferHistoryEntry(
            id=item.get("id", 0),
            transfer_date_timestamp=item.get("transferDateTimestamp", 0),
            type=item.get("type", 0),
            transfer_fee=item.get("transferFee", 0),
            transfer_fee_description=item.get("transferFeeDescription", None),
            from_team_name=item.get("fromTeamName", None),
            to_team_name=item.get("toTeamName", None),
            transfer_fee_raw=parse_transfer_fee_raw(item.get("transferFeeRaw", {})),
            transfer_from=parse_team(raw_from),
            transfer_to=parse_team(raw_to),
        )
        history.entries.append(entry)
    return history

"""Promiedos match odds and parsers."""

from dataclasses import dataclass, field


@dataclass
class OddsOption:
    """One betting outcome and its odds."""

    name: str = field(default=None)
    value: float = field(default=0.0)
    trend: int = field(default=0)


@dataclass
class MainOdds:
    """Home-win, draw and away-win betting outcomes."""

    options: list[OddsOption] = field(default_factory=list)


def parse_odds_option(data: dict) -> OddsOption:
    """
    Parse the odds option data.
    """
    return OddsOption(
        name=data.get("name", None),
        value=data.get("value", 0.0),
        trend=data.get("trend", 0),
    )


def parse_main_odds(data: dict) -> MainOdds:
    """
    Parse the main odds data.
    """
    options_data = data.get("options", [])
    return MainOdds(options=[parse_odds_option(opt) for opt in options_data])

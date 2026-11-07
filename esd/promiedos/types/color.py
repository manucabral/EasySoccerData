"""Promiedos display colors and parser."""

from dataclasses import dataclass, field


@dataclass
class Color:
    """Background and text colors reported by Promiedos."""

    color: str = field(default=None)
    text_color: str = field(default=None)


def parse_color(data: dict) -> Color:
    """
    Parse the colors data.
    """
    return Color(color=data.get("color", ""), text_color=data.get("text_color", ""))

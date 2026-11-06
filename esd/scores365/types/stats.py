"""
365Scores match statistics dataclasses.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GameStatItem:
    """
    A single team statistic item from a 365Scores match.
    """

    id: int = None
    name: str = None
    category_id: int = None
    category_name: str = None
    competitor_id: int = None
    value: str = None
    percentage: float | None = None
    is_major: bool = False


def parse_game_stats(data: dict) -> list[GameStatItem]:
    """
    Parse match statistics from a 365Scores stats payload.
    """
    if not data:
        return []
    stats: list[GameStatItem] = []
    for item in data.get("statistics", []) or []:
        raw_pct = item.get("valuePercentage")
        stats.append(
            GameStatItem(
                id=item.get("id"),
                name=item.get("name"),
                category_id=item.get("categoryId"),
                category_name=item.get("categoryName"),
                competitor_id=item.get("competitorId"),
                value=str(item.get("value", "")),
                percentage=float(raw_pct)
                if isinstance(raw_pct, (int, float))
                else None,
                is_major=bool(item.get("isMajor", False)),
            )
        )
    return stats

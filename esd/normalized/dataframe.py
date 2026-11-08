"""Stable column types for normalized records, including empty tables."""

from __future__ import annotations

from dataclasses import fields

from ..utils import to_dataframe
from .models import SCHEMA_VERSION
from .schema import TABLE_MODELS, _column_dtype


def normalized_to_dataframe(objects: list, *, table: str):
    """Export normalized records using the current normalized schema version.

    table selects matches, teams, standings, match_stats, player_stats, shots,
    players, market_values, transfers, lineups, player_match_stats or match_events.
    All rows must use the normalized model for that table. IDs and names use
    nullable string, counts use Int64, metrics use Float64, flags use boolean, and kickoff uses
    datetime64[ns, UTC]. Rows are exported without entity matching or
    deduplication. Status values keep the source's codes and text.
    """
    if table not in TABLE_MODELS:
        raise ValueError(f"Unknown normalized table: {table!r}. Choose from {tuple(TABLE_MODELS)}")
    model = TABLE_MODELS[table]
    if any(not isinstance(obj, model) for obj in objects):
        raise TypeError(f"Table {table!r} requires {model.__name__} records")
    dtypes = {}
    for field in fields(model):
        if field.name != "kickoff":
            dtypes[field.name] = _column_dtype(field.name)
    frame = to_dataframe(
        objects,
        dtypes=dtypes,
        datetime_columns={"kickoff": None} if table == "matches" else None,
    )
    if table == "matches":
        frame["kickoff"] = frame["kickoff"].astype("datetime64[ns, UTC]")
    frame = frame[[field.name for field in fields(model)]]
    frame.attrs.update(schema_version=SCHEMA_VERSION, table=table)
    return frame

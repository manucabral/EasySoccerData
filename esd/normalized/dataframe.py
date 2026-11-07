"""Stable column types for normalized records, including empty tables."""

from __future__ import annotations

from dataclasses import fields

from ..utils import to_dataframe
from .models import SCHEMA_VERSION
from .schema import FLOAT_COLUMNS, INTEGER_COLUMNS, TABLE_MODELS


def normalized_to_dataframe(objects: list, *, table: str):
    """Export normalized records with schema version 1.

    table selects matches, teams, standings, match_stats, player_stats, shots,
    players, market_values or transfers.
    All rows must be instances
    of the matching normalized model. IDs/names use nullable string, counts use
    Int64, metrics use Float64, and kickoff uses datetime64[ns, UTC]. No entity matching or deduplication
    is performed. Source status values remain provider-specific.
    """
    if table not in TABLE_MODELS:
        raise ValueError(f"Unknown normalized table: {table!r}. Choose from {tuple(TABLE_MODELS)}")
    model = TABLE_MODELS[table]
    if any(not isinstance(obj, model) for obj in objects):
        raise TypeError(f"Table {table!r} requires {model.__name__} records")
    dtypes = {}
    for field in fields(model):
        if field.name != "kickoff":
            dtypes[field.name] = (
                "Int64" if field.name in INTEGER_COLUMNS else
                "Float64" if field.name in FLOAT_COLUMNS else "string"
            )
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

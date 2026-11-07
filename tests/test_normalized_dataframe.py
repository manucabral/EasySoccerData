"""Common tables have the same columns and types across supported sources."""

import pytest

from esd import (
    NormalizedMatch,
    NormalizedStanding,
    NormalizedTeam,
    normalize_match,
    normalize_standings,
    normalize_team,
    normalized_to_dataframe,
)
from esd.espn.types import ESPNMatch, ESPNStandingRow, ESPNStandingTable, ESPNTeam
from esd.scores365.types import Competitor, Game, StandingRow, StandingTable

pd = pytest.importorskip("pandas")


@pytest.mark.parametrize("table, records", [
    ("matches", [
        normalize_match(ESPNMatch(id="001", date="2026-11-06T21:00Z")),
        normalize_match(Game(id=1)),
    ]),
    ("teams", [normalize_team(ESPNTeam(id="001")), normalize_team(Competitor(id=1))]),
    ("standings", [
        normalize_standings(ESPNStandingTable(rows=[ESPNStandingRow(points=0)]))[0],
        normalize_standings(StandingTable(rows=[StandingRow(points=3)]))[0],
    ]),
])
def test_provider_tables_share_schema_with_empty_and_missing_records(table, records):
    first = normalized_to_dataframe(records[:1], table=table)
    second = normalized_to_dataframe(records[1:], table=table)
    empty = normalized_to_dataframe([], table=table)
    assert first.dtypes.equals(second.dtypes)
    assert first.dtypes.equals(empty.dtypes)
    combined = pd.concat([first, second], ignore_index=True)
    assert combined["source"].tolist() == ["espn", "scores365"]
    assert combined.attrs == {"schema_version": "1", "table": table}
    assert len(combined) == 2
    if table == "matches":
        assert str(combined["kickoff"].dtype) == "datetime64[ns, UTC]"
        assert pd.isna(combined.loc[1, "kickoff"])
        assert combined["home_score"].isna().all()


def test_join_uses_source_and_team_id_to_avoid_collisions():
    games = [
        normalize_match(ESPNMatch(id="a", home_team=ESPNTeam(id="1"))),
        normalize_match(Game(id=2, home_team=Competitor(id=1))),
    ]
    teams = [normalize_team(ESPNTeam(id="1", name="ESPN team")),
             normalize_team(Competitor(id=1, name="365 team"))]
    matches = normalized_to_dataframe(games, table="matches")
    clubs = normalized_to_dataframe(teams, table="teams")
    joined = matches.merge(clubs, left_on=["source", "home_team_id"],
                           right_on=["source", "team_id"], validate="many_to_one")
    assert joined["name"].tolist() == ["ESPN team", "365 team"]


@pytest.mark.parametrize("table, record", [
    ("matches", NormalizedTeam("espn")),
    ("teams", NormalizedStanding("espn")),
    ("standings", NormalizedMatch("espn")),
])
def test_wrong_record_type_raises(table, record):
    with pytest.raises(TypeError, match="requires"):
        normalized_to_dataframe([record], table=table)


def test_unknown_table_raises_even_for_empty_input():
    with pytest.raises(ValueError, match="Unknown normalized table"):
        normalized_to_dataframe([], table="other")

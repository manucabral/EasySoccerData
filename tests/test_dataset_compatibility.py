"""Cross-source matches require identities, ordered teams and a unique time match."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

import esd


def dataset(source, league, match_id, home, away):
    timestamp = datetime(2024, 8, 16, 19, tzinfo=timezone.utc)
    return esd.SoccerDataset(
        esd.DatasetMetadata(
            source,
            league,
            2024,
            ("matches", "teams"),
            timestamp,
            timestamp,
            expected_tasks=("matches:1",),
            successful_tasks=("matches:1",),
        ),
        match_records=(
            esd.NormalizedMatch(
                source,
                match_id=match_id,
                competition_id=league,
                home_team_id=home,
                home_team_name="Same name",
                away_team_id=away,
                away_team_name="Same name",
                kickoff=timestamp,
            ),
        ),
    )


@pytest.fixture
def pair():
    return dataset("espn", "eng.1", "e1", "1", "2"), dataset("understat", "EPL", "u1", "11", "22")


@pytest.fixture
def identities():
    return esd.IdentityMap(
        [
            esd.EntityAlias("competition", "england-premier", "espn", "eng.1"),
            esd.EntityAlias("competition", "england-premier", "understat", "EPL"),
            esd.EntityAlias("team", "club-a", "espn", "1"),
            esd.EntityAlias("team", "club-a", "understat", "11"),
            esd.EntityAlias("team", "club-b", "espn", "2"),
            esd.EntityAlias("team", "club-b", "understat", "22"),
        ]
    )


def test_common_schema_does_not_imply_identity_or_name_equivalence(pair):
    report = esd.check_dataset_compatibility(*pair)
    assert report.schema_compatible and not report.identity_compatible and not report.can_match
    result = esd.link_dataset_matches(*pair)
    assert (
        not result.links and result.unmatched_left == ("e1",) and result.unmatched_right == ("u1",)
    )


def test_explicit_identities_link_without_changing_native_records(pair, identities):
    result = esd.link_dataset_matches(*pair, identities=identities)
    assert result.compatibility.can_match
    assert len(result.links) == 1
    assert result.links[0] == esd.MatchLink("espn", "e1", "understat", "u1", 0)
    assert not result.unmatched_left and not result.ambiguous_left
    assert pair[0].match_records[0].home_team_id == "1"


@pytest.mark.parametrize(
    "change", ["reversed", "time", "date_missing", "team_unknown", "competition"]
)
def test_no_link_when_evidence_is_insufficient(pair, identities, change):
    left, right = pair
    row = right.match_records[0]
    if change == "reversed":
        row = replace(row, home_team_id="22", away_team_id="11")
    elif change == "time":
        row = replace(row, kickoff=row.kickoff + timedelta(days=1))
    elif change == "date_missing":
        row = replace(row, kickoff=None)
    elif change == "team_unknown":
        row = replace(row, home_team_id="99")
    else:
        row = replace(row, competition_id="other")
    result = esd.link_dataset_matches(
        left, replace(right, match_records=(row,)), identities=identities
    )
    assert not result.links and result.unmatched_right == ("u1",)


@pytest.mark.parametrize("duplicate_side", ["left", "right"])
def test_ambiguity_is_reported_in_both_directions(pair, identities, duplicate_side):
    left, right = pair
    if duplicate_side == "right":
        right = replace(
            right,
            match_records=(*right.match_records, replace(right.match_records[0], match_id="u2")),
        )
    else:
        left = replace(
            left, match_records=(*left.match_records, replace(left.match_records[0], match_id="e2"))
        )
    result = esd.link_dataset_matches(left, right, identities=identities)
    assert not result.links and result.ambiguous_left and result.ambiguous_right
    assert not result.unmatched_left and not result.unmatched_right


def test_time_tolerance_and_source_namespaces(pair, identities):
    left, right = pair
    right = replace(
        right,
        match_records=(
            replace(
                right.match_records[0],
                match_id="e1",
                kickoff=right.match_records[0].kickoff + timedelta(seconds=120),
            ),
        ),
    )
    assert len(esd.link_dataset_matches(left, right, identities=identities).links) == 1
    assert not esd.link_dataset_matches(
        left, right, identities=identities, tolerance_seconds=60
    ).links


def test_same_source_ids_need_no_external_mapping(pair):
    left = pair[0]
    assert esd.link_dataset_matches(left, left).compatibility.can_match
    assert len(esd.link_dataset_matches(left, left).links) == 1


@pytest.mark.parametrize("change", ["version", "duplicate", "source", "naive"])
def test_invalid_schemas_cannot_link(pair, identities, change):
    left, right = pair
    if change == "version":
        right = replace(right, metadata=replace(right.metadata, schema_version="999"))
    elif change == "duplicate":
        right = replace(right, match_records=right.match_records * 2)
    elif change == "source":
        right = replace(right, match_records=(replace(right.match_records[0], source="other"),))
    else:
        right = replace(
            right, match_records=(replace(right.match_records[0], kickoff=datetime(2024, 8, 16)),)
        )
    assert not esd.check_dataset_compatibility(left, right, identities=identities).schema_compatible
    with pytest.raises(ValueError):
        esd.link_dataset_matches(left, right, identities=identities)


def test_no_match_table_and_partial_coverage_reported(pair):
    left, right = pair
    right = replace(
        right,
        metadata=replace(right.metadata, tables=("teams",), successful_tasks=()),
        match_records=(),
    )
    report = esd.check_dataset_compatibility(left, right)
    assert report.schema_compatible and not report.can_match
    assert any("incomplete" in issue for issue in report.issues)
    with pytest.raises(ValueError):
        esd.link_dataset_matches(left, right)


def test_identity_conflicts_rejected():
    with pytest.raises(ValueError, match="Conflicting"):
        esd.IdentityMap(
            [esd.EntityAlias("team", "a", "espn", "1"), esd.EntityAlias("team", "b", "espn", "1")]
        )


def test_team_tables_require_their_own_identity_mappings(pair):
    left, right = pair
    left = replace(left, team_records=(esd.NormalizedTeam("espn", "1", "Home"),))
    right = replace(right, team_records=(esd.NormalizedTeam("understat", "11", "Home"),))
    identities = esd.IdentityMap(
        [
            esd.EntityAlias("competition", "league", "espn", "eng.1"),
            esd.EntityAlias("competition", "league", "understat", "EPL"),
        ]
    )
    report = esd.check_dataset_compatibility(left, right, identities=identities)
    assert not report.identity_compatible
    assert any("team/standings" in issue for issue in report.issues)


@pytest.mark.parametrize("tolerance", [-1, float("nan"), float("inf"), True])
def test_invalid_tolerance_rejected(pair, tolerance):
    with pytest.raises(ValueError):
        esd.link_dataset_matches(*pair, tolerance_seconds=tolerance)

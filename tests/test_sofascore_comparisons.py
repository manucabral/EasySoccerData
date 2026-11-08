"""Sofascore comparisons use explicit identities, unknown scope and exact tasks."""

from dataclasses import replace
from datetime import timedelta

import pytest

import esd
from tests.test_event_comparison import NOW
from tests.test_event_comparison import dataset as event_dataset
from tests.test_player_comparison import dataset as player_dataset


@pytest.fixture
def trio():
    result = []
    for source, identifier, competition, home, away, player, period in (
        ("espn", "1", "cup", "10", "20", "101", "2"),
        ("scores365", "2", "72", "30", "40", "201", "9"),
        ("sofascore", "3", "7", "50", "60", "301", None),
    ):
        events = event_dataset(source, identifier, competition, home, away, player, period)
        players = player_dataset(source, identifier, competition, home, away, player)
        task = f"{'match_details' if source == 'espn' else 'lineups'}:{identifier}"
        tasks = (task,) if source != "sofascore" else ("match:3", "lineups:3", "match_events:3")
        metadata = replace(players.metadata, tables=("matches", "lineups", "player_match_stats", "match_events"),
                           expected_tasks=tasks, successful_tasks=tasks,
                           response_fetched_at=tuple((key, (NOW + timedelta(seconds=i)).isoformat()) for i, key in enumerate(tasks)))
        result.append(replace(players, metadata=metadata, match_event_records=events.match_event_records))
    return tuple(result)


@pytest.fixture
def identities():
    return esd.IdentityMap([
        esd.EntityAlias(kind, canonical, source, native)
        for kind, canonical, natives in (("competition", "cup", ("cup", "72", "7")),
                                         ("team", "home", ("10", "30", "50")),
                                         ("team", "away", ("20", "40", "60")),
                                         ("player", "scorer", ("101", "201", "301")),
                                         ("player", "outgoing", ("102", "202", "302")))
        for source, native in zip(("espn", "scores365", "sofascore"), natives)
    ])


@pytest.mark.parametrize("other", [0, 1])
@pytest.mark.parametrize("reverse", [False, True])
def test_sofa_without_period_is_explicitly_unresolved_by_default(trio, identities, other, reverse):
    pair = (trio[other], trio[2]) if not reverse else (trio[2], trio[other])
    report = esd.compare_match_events(*pair, identities=identities)
    assert len(report.linkage.links) == 1 and len(report.unresolved) == 2
    assert any(row.reason == "period_unknown" for row in report.rows)
    assert not report.allow_unknown_period


@pytest.mark.parametrize("other", [0, 1])
@pytest.mark.parametrize("reverse", [False, True])
def test_opt_in_pairs_unknown_scope_without_inventing_native_periods(trio, identities, other, reverse):
    pair = (trio[other], trio[2]) if not reverse else (trio[2], trio[other])
    report = esd.compare_match_events(*pair, identities=identities, allow_unknown_period=True)
    row, = report.rows
    assert row.status == "equal" and "source_period" in row.unknown_fields
    assert report.allow_unknown_period and not report.unresolved
    sofa = row.left_event if reverse else row.right_event
    assert sofa.source_period is None and sofa.minute == 59
    coverage = report.left_coverage if reverse else report.right_coverage
    assert coverage[0].successful and coverage[0].fetched_at == NOW + timedelta(seconds=2)


def test_explicit_sofa_period_aliases_compare_known_scope_and_reject_mismatches(trio, identities):
    native = replace(trio[2], match_event_records=(replace(trio[2].match_event_records[0], source_period="reviewed-native"),))
    report = esd.compare_match_events(trio[0], native, identities=identities,
                                     period_aliases={("sofascore", "reviewed-native"): "second_half"})
    assert len(report.rows) == 1 and "source_period" not in report.rows[0].unknown_fields
    report = esd.compare_match_events(trio[0], native, identities=identities, allow_unknown_period=True,
                                     period_aliases={("sofascore", "reviewed-native"): "first_half"})
    assert len(report.unresolved) == 2 and all(row.status.startswith("unmatched") for row in report.rows)


def test_unknown_period_policy_does_not_choose_between_repeated_candidates(trio, identities):
    native = trio[2].match_event_records[0]
    sofa = replace(trio[2], match_event_records=(native, replace(native, source_order=2, minute=60)))
    report = esd.compare_match_events(trio[0], sofa, identities=identities, allow_unknown_period=True)
    assert len(report.rows) == 3 and all(row.status.startswith("ambiguous") for row in report.rows)


def test_unknown_period_does_not_guess_shootouts_or_bench_minutes(trio, identities):
    for changes, reason in (({"is_shootout": None}, "shootout_unknown"), ({"minute": None}, "minute_unknown")):
        sofa = replace(trio[2], match_event_records=(replace(trio[2].match_event_records[0], **changes),))
        report = esd.compare_match_events(trio[0], sofa, identities=identities, allow_unknown_period=True)
        assert len(report.unresolved) == 2 and report.rows[-1].reason == reason
    sofa = replace(trio[2], match_event_records=(replace(trio[2].match_event_records[0], is_shootout=True, minute=None, added_minute=None),))
    report = esd.compare_match_events(trio[0], sofa, identities=identities, allow_unknown_period=True)
    assert len(report.unresolved) == 2  # Explicitly different match/shootout domains never pair.


def test_shootout_and_substitution_roles_remain_explicit(trio, identities):
    first = replace(trio[0], match_event_records=(replace(trio[0].match_event_records[0], event_type="penalty_scored",
                                                        is_shootout=True, source_period="5", minute=None, added_minute=None),))
    sofa = replace(trio[2], match_event_records=(replace(trio[2].match_event_records[0], event_type="penalty_missed",
                                                       is_shootout=True, minute=None, added_minute=None),))
    row, = esd.compare_match_events(first, sofa, identities=identities, allow_unknown_period=True).rows
    assert row.differences == ("event_type",) and "source_period" in row.unknown_fields
    first = replace(trio[0], match_event_records=(replace(trio[0].match_event_records[0], event_type="substitution",
                                                        related_player_id="102", player_role="incoming", related_player_role="outgoing"),))
    sofa = replace(trio[2], match_event_records=(replace(trio[2].match_event_records[0], event_type="substitution",
                                                       related_player_id="302", player_role="incoming", related_player_role="outgoing"),))
    assert len(esd.compare_match_events(first, sofa, identities=identities, allow_unknown_period=True).rows) == 1


def test_sofa_same_source_native_event_id_anchors_changed_annulment(trio):
    sofa = replace(trio[2], match_event_records=(replace(trio[2].match_event_records[0], event_id="native", rescinded=False),))
    changed = replace(sofa, match_event_records=(replace(sofa.match_event_records[0], minute=None, rescinded=True),))
    report = esd.compare_match_events(sofa, changed)
    assert report.rows[0].reason == "native_event_id" and report.rows[0].differences == ("rescinded",)
    assert "source_period" in report.rows[0].unknown_fields


@pytest.mark.parametrize("other", [0, 1])
def test_sofa_player_positions_models_and_original_lineup_timestamp(trio, identities, other):
    report = esd.compare_match_players(trio[other], trio[2], identities=identities,
                                       position_aliases={(trio[other].metadata.source, "MID"): "midfielder", ("sofascore", "MID"): "midfielder"})
    row, = report.rows
    assert row.status == "equal" and "position" not in row.unknown_fields
    assert report.right_coverage[0].fetched_at == NOW + timedelta(seconds=1)
    assert row.right_fetched_at == NOW + timedelta(seconds=1)
    assert all(item.status == "source_specific" and item.delta is None for item in report.statistics if item.metric in ("xg", "xa", "source_rating"))
    assert next(item for item in report.statistics if item.metric == "minutes").status == "missing_both"


def test_lineup_fetch_cannot_supply_incident_success_or_dates(trio, identities):
    sofa = replace(trio[2], match_event_records=(),
                   metadata=replace(trio[2].metadata, successful_tasks=("match:3", "lineups:3"),
                                    response_fetched_at=trio[2].metadata.response_fetched_at[:2]),
                   errors=(esd.DatasetIssue("match_events", "3", "SourceBlocked", "Blocked incidents"),))
    report = esd.compare_match_events(trio[0], sofa, identities=identities, allow_unknown_period=True)
    assert not report.right_coverage[0].successful and report.right_coverage[0].fetched_at is None
    assert not report.right_complete and report.right_errors == sofa.errors
    players = esd.compare_match_players(trio[0], sofa, identities=identities)
    assert players.right_coverage[0].successful and players.right_coverage[0].fetched_at is not None


@pytest.mark.parametrize("value", [None, 1, "true"])
def test_unknown_period_policy_requires_boolean(trio, value):
    with pytest.raises(ValueError, match="allow_unknown_period"):
        esd.compare_match_events(trio[0], trio[2], allow_unknown_period=value)


def test_three_source_comparison_roundtrips_keep_nullable_frames(trio, identities, tmp_path):
    pytest.importorskip("pyarrow")
    restored = tuple(esd.open_dataset(item.save(tmp_path / item.metadata.source)) for item in trio)
    before = esd.compare_match_events(trio[0], trio[2], identities=identities, allow_unknown_period=True)
    assert esd.compare_match_events(restored[0], restored[2], identities=identities, allow_unknown_period=True) == before
    assert esd.compare_match_players(restored[1], restored[2], identities=identities) == esd.compare_match_players(trio[1], trio[2], identities=identities)
    pytest.importorskip("pandas")
    assert str(before.to_dataframe().right_rescinded.dtype) == "boolean"

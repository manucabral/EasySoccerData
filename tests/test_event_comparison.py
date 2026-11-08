"""Event comparisons require explicit identities, scope and mutual uniqueness."""

from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone

import pytest

import esd

NOW = datetime(2026, 11, 3, 20, tzinfo=timezone.utc)


def dataset(source, identifier, competition, home, away, player, period):
    task = f"match_details:{identifier}" if source == "espn" else f"match_events:{identifier}"
    return esd.SoccerDataset(
        esd.DatasetMetadata(source, competition, 2026, ("matches", "match_events"), NOW, NOW,
                            expected_tasks=(task,), successful_tasks=(task,), response_fetched_at=((task, NOW.isoformat()),)),
        match_records=(esd.NormalizedMatch(source, identifier, competition_id=competition,
                                           home_team_id=home, away_team_id=away, kickoff=NOW),),
        match_event_records=(esd.NormalizedMatchEvent(source, identifier, event_id="e1" if source == "espn" else None,
                                                      source_order=None if source == "espn" else 1, event_type="goal",
                                                      source_period=period, minute=59, added_minute=0,
                                                      is_shootout=False, team_id=away, player_id=player),),
    )


@pytest.fixture
def pair():
    return (dataset("espn", "1", "cup", "10", "20", "101", "2"),
            dataset("scores365", "2", "72", "30", "40", "201", "9"))


@pytest.fixture
def identities():
    return esd.IdentityMap([
        esd.EntityAlias(kind, canonical, source, native)
        for kind, canonical, natives in (("competition", "cup", ("cup", "72")), ("team", "home", ("10", "30")),
                                         ("team", "away", ("20", "40")), ("player", "scorer", ("101", "201")),
                                         ("player", "outgoing", ("102", "202")))
        for source, native in zip(("espn", "scores365"), natives)
    ])


def event(dataset, **changes):
    return replace(dataset, match_event_records=(replace(dataset.match_event_records[0], **changes),))


def test_event_tables_are_recognized_by_existing_compatibility_and_match_linker(pair, identities):
    assert esd.check_dataset_compatibility(*pair, identities=identities).can_match
    assert len(esd.link_dataset_matches(*pair, identities=identities).links) == 1


def test_explicit_player_aliases_extend_without_mutation_and_export_for_storage(identities):
    alias = esd.EntityAlias("player", "another", "espn", "103")
    extended = identities.with_aliases([alias])
    assert extended.resolve("player", "espn", "103") == "another"
    assert identities.resolve("player", "espn", "103") is None
    assert esd.IdentityMap(extended.aliases).aliases == extended.aliases
    with pytest.raises(ValueError, match="Conflicting"):
        identities.with_aliases([esd.EntityAlias("player", "wrong", "espn", "101")])
    assert extended.resolve("team", "espn", "101") is None


def test_observed_equality_does_not_assert_unknown_annulments_or_change_native_ids(pair, identities):
    report = esd.compare_match_events(*pair, identities=identities)
    row, = report.rows
    assert row.status == "equal" and row.unknown_fields == ("rescinded",)
    assert row.left_event.player_id == "101" and row.right_event.player_id == "201"
    assert row.left_fetched_at == row.right_fetched_at == NOW
    assert report.left_coverage[0].successful and report.left_coverage[0].record_count == 1
    assert not report.differences and not report.unresolved
    with pytest.raises(FrozenInstanceError):
        row.status = "different"


@pytest.mark.parametrize("changes,fields", [({"minute": 60}, ("minute",)), ({"added_minute": 1}, ("added_minute",)),
                                          ({"event_type": "own_goal"}, ("event_type",)), ({"team_id": "30"}, ("team_id",))])
def test_known_observation_differences_survive_candidate_tolerance(pair, identities, changes, fields):
    report = esd.compare_match_events(pair[0], event(pair[1], **changes), identities=identities)
    row, = report.rows
    assert row.status == "different" and row.differences == fields and report.differences == (row,)


def test_annulments_are_compared_only_when_observed_on_both_sides(pair, identities):
    report = esd.compare_match_events(event(pair[0], rescinded=True), event(pair[1], rescinded=False), identities=identities)
    assert report.rows[0].differences == ("rescinded",)
    row, = esd.compare_match_events(pair[0], event(pair[1], rescinded=True), identities=identities).rows
    assert row.status == "equal" and "rescinded" in row.unknown_fields


@pytest.mark.parametrize("side", [0, 1])
def test_unknown_added_time_is_not_zero(pair, identities, side):
    values = list(pair)
    values[side] = event(values[side], added_minute=None)
    row, = esd.compare_match_events(*values, identities=identities).rows
    assert row.status == "equal" and "added_minute" in row.unknown_fields and not row.differences


@pytest.mark.parametrize("changes,reason", [({"player_id": None}, "player_identity_unknown"),
                                          ({"player_id": "999"}, "player_identity_unknown"),
                                          ({"team_id": None}, "team_identity_unknown"),
                                          ({"is_shootout": None}, "shootout_unknown"),
                                          ({"source_period": None}, "period_unknown"),
                                          ({"source_period": "custom"}, "period_unknown"),
                                          ({"minute": None}, "minute_unknown")])
def test_missing_identity_or_scope_stays_unresolved(pair, identities, changes, reason):
    report = esd.compare_match_events(event(pair[0], **changes), pair[1], identities=identities)
    assert len(report.rows) == 2 and not report.differences
    left = next(row for row in report.rows if row.left_event is not None)
    assert left.status == "unresolved_left" and left.reason == reason
    assert all(row.left_event is None or row.right_event is None for row in report.rows)


def test_separate_365_athlete_id_does_not_replace_member_identity(pair, identities):
    right = event(pair[1], player_id="unmapped-member", source_athlete_id="201")
    report = esd.compare_match_events(pair[0], right, identities=identities)
    assert not any(row.left_event and row.right_event for row in report.rows)


def test_unknown_periods_can_use_caller_reviewed_aliases_and_keep_native_values(pair, identities):
    right = event(pair[1], source_period="custom")
    report = esd.compare_match_events(pair[0], right, identities=identities,
                                      period_aliases={("scores365", "custom"): "second_half"})
    assert report.rows[0].status == "equal" and report.rows[0].right_event.source_period == "custom"
    assert ("scores365", "custom", "second_half") in report.period_aliases


@pytest.mark.parametrize("change", [{"minute": 61}, {"source_period": "7"}, {"is_shootout": True}])
def test_events_outside_time_or_period_or_shootout_scope_are_not_forced(pair, identities, change):
    if change.get("is_shootout"):
        change = dict(change, minute=None, added_minute=None)
    report = esd.compare_match_events(pair[0], event(pair[1], **change), identities=identities)
    assert len(report.unresolved) == 2 and not report.differences


def test_two_nearby_events_are_ambiguous_in_both_directions_without_nearest_guess(pair, identities):
    right = replace(pair[1], match_event_records=(pair[1].match_event_records[0],
                                                replace(pair[1].match_event_records[0], source_order=2, minute=60)))
    report = esd.compare_match_events(pair[0], right, identities=identities)
    assert len(report.rows) == 3
    assert [row.status for row in report.rows] == ["ambiguous_left", "ambiguous_right", "ambiguous_right"]
    assert report.rows[0].candidate_keys == ("order:1", "order:2")


def test_repeated_shootout_takers_are_ambiguous_and_minutes_never_select_attempts(pair, identities):
    left = event(pair[0], event_type="penalty_scored", is_shootout=True, source_period="5", minute=None, added_minute=None)
    right = event(pair[1], event_type="penalty_missed", is_shootout=True, source_period="11", minute=None, added_minute=None)
    row, = esd.compare_match_events(left, right, identities=identities).rows
    assert row.status == "different" and row.differences == ("event_type",)
    right = replace(right, match_event_records=(*right.match_event_records, replace(right.match_event_records[0], source_order=2)))
    report = esd.compare_match_events(left, right, identities=identities)
    assert all(row.status.startswith("ambiguous") for row in report.rows)


def test_substitutions_require_both_reviewed_roles_and_both_player_ids(pair, identities):
    left = event(pair[0], event_type="substitution", player_role="incoming", related_player_role="outgoing", related_player_id="102")
    right = event(pair[1], event_type="substitution", player_role="incoming", related_player_role="outgoing", related_player_id="202")
    assert esd.compare_match_events(left, right, identities=identities).rows[0].status == "equal"
    report = esd.compare_match_events(left, event(right, related_player_id="missing"), identities=identities)
    assert any(row.reason == "related_player_identity_unknown" for row in report.rows)
    report = esd.compare_match_events(left, event(right, player_role=None), identities=identities)
    assert any(row.reason == "substitution_roles_unknown" for row in report.rows)


def test_native_same_source_event_id_anchors_revisions_with_changed_observations(pair):
    left = event(pair[0], player_id=None, source_period=None, is_shootout=None)
    right = event(left, minute=78, rescinded=True)
    report = esd.compare_match_events(left, right, minute_tolerance=0)
    row, = report.rows
    assert row.reason == "native_event_id" and row.differences == ("minute",)
    assert set(row.unknown_fields) >= {"player_id", "source_period", "is_shootout", "rescinded"}


def test_different_native_ids_in_one_source_are_distinct_events(pair):
    report = esd.compare_match_events(pair[0], event(pair[0], event_id="other"))
    assert len(report.unresolved) == 2 and not any(row.left_event and row.right_event for row in report.rows)


def test_conflicting_event_task_times_do_not_choose_one_arbitrarily(pair, identities):
    right = replace(pair[1], metadata=replace(pair[1].metadata, expected_tasks=("match_events:2", "lineups:2"),
                                            successful_tasks=("match_events:2", "lineups:2"),
                                            response_fetched_at=(("match_events:2", NOW.isoformat()),
                                                                 ("lineups:2", (NOW - timedelta(days=1)).isoformat()))))
    report = esd.compare_match_events(pair[0], right, identities=identities)
    assert report.rows[0].right_fetched_at is None and report.right_coverage[0].fetched_at is None


def test_unlinked_match_events_and_excluded_types_are_never_silently_lost(pair):
    left = replace(pair[0], match_event_records=(*pair[0].match_event_records, replace(pair[0].match_event_records[0], event_id="phase", event_type="other")))
    report = esd.compare_match_events(left, pair[1])
    assert len(report.rows) == 2 and len(report.excluded_left) == 1
    assert all(row.reason == "match_unlinked" for row in report.rows)


def test_empty_successful_feed_is_distinct_from_failed_missing_feed(pair, identities):
    empty = replace(pair[1], match_event_records=())
    report = esd.compare_match_events(pair[0], empty, identities=identities)
    assert report.right_coverage[0].successful and report.right_coverage[0].record_count == 0
    failed = replace(empty, metadata=replace(empty.metadata, successful_tasks=(), response_fetched_at=()),
                     errors=(esd.DatasetIssue("match_events", "2", "SourceBlocked", "Blocked"),))
    report = esd.compare_match_events(pair[0], failed, identities=identities)
    assert not report.right_coverage[0].successful and not report.right_complete
    assert report.right_errors == failed.errors and report.rows[0].right_fetched_at is None


def test_original_event_fetches_are_exact_and_never_context_or_loader_times(pair, identities):
    old = NOW - timedelta(days=2)
    right = replace(pair[1], metadata=replace(pair[1].metadata, expected_tasks=("lineups:2",), successful_tasks=("lineups:2",),
                                            cached_tasks=("lineups:2",), response_fetched_at=(("lineups:2", old.isoformat()),)))
    row, = esd.compare_match_events(pair[0], right, identities=identities).rows
    assert row.right_fetched_at == old
    right = replace(right, metadata=replace(right.metadata, cached_tasks=(), response_fetched_at=(("match:2", NOW.isoformat()),)))
    assert esd.compare_match_events(pair[0], right, identities=identities).rows[0].right_fetched_at is None


@pytest.mark.parametrize("options", [{"minute_tolerance": True}, {"minute_tolerance": -1}, {"minute_tolerance": 0.5},
                                    {"tolerance_seconds": float("nan")}, {"tolerance_seconds": True},
                                    {"event_types": []}, {"event_types": "goal"}, {"event_types": ["other"]},
                                    {"period_aliases": []}, {"period_aliases": {"invalid": "period"}},
                                    {"period_aliases": {("unknown", "1"): "period"}}, {"identities": []}])
def test_bad_options_fail_explicitly(pair, options):
    with pytest.raises((TypeError, ValueError)):
        esd.compare_match_events(*pair, **options)


@pytest.mark.parametrize("change", ["orphan", "duplicate", "unselected", "bad_clock", "unsupported"])
def test_invalid_datasets_and_unsupported_sources_fail(pair, change):
    left, right = pair
    if change == "orphan":
        left = event(left, match_id="missing")
    elif change == "duplicate":
        left = replace(left, match_event_records=left.match_event_records * 2)
    elif change == "unselected":
        left = replace(left, metadata=replace(left.metadata, tables=("matches",)), match_event_records=())
    elif change == "bad_clock":
        left = event(left, minute=-1)
    else:
        left = replace(left, metadata=replace(left.metadata, source="understat"),
                       match_records=(replace(left.match_records[0], source="understat"),),
                       match_event_records=(replace(left.match_event_records[0], source="understat"),))
    with pytest.raises(ValueError):
        esd.compare_match_events(left, right)


def test_dataframe_uses_fixed_nullable_columns_and_snapshot_roundtrip(pair, identities, tmp_path):
    pytest.importorskip("pandas")
    pytest.importorskip("pyarrow")
    report = esd.compare_match_events(*pair, identities=identities)
    frame = report.to_dataframe()
    empty = esd.compare_match_events(replace(pair[0], match_event_records=()), replace(pair[1], match_event_records=()), identities=identities).to_dataframe()
    assert frame.dtypes.equals(empty.dtypes)
    assert str(frame.left_minute.dtype) == "Int64" and str(frame.right_rescinded.dtype) == "boolean"
    assert str(frame.left_fetched_at.dtype) == "datetime64[ns, UTC]"
    assert frame.attrs == {"report": "match_events", "report_version": "1"}
    reopened = [esd.open_dataset(item.save(tmp_path / str(index))) for index, item in enumerate(pair)]
    assert esd.compare_match_events(*reopened, identities=identities) == report

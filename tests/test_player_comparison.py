"""Player comparisons preserve unknowns, ambiguous identities and source models."""

import builtins
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

import esd

NOW = datetime(2026, 11, 3, 20, tzinfo=timezone.utc)


def dataset(source, identifier, competition, home, away, player):
    task = f"{'match_details' if source == 'espn' else 'lineups'}:{identifier}"
    return esd.SoccerDataset(
        esd.DatasetMetadata(source, competition, 2026, ("matches", "lineups", "player_match_stats"), NOW, NOW,
                            expected_tasks=(task,), successful_tasks=(task,), response_fetched_at=((task, NOW.isoformat()),)),
        match_records=(esd.NormalizedMatch(source, identifier, competition_id=competition,
                                           home_team_id=home, away_team_id=away, kickoff=NOW),),
        lineup_records=(esd.NormalizedLineup(source, identifier, away, player, "Same display name",
                                             starter=False, jersey_number="01", home_away="away", position="MID"),),
        player_match_stat_records=(esd.NormalizedPlayerMatchStats(source, identifier, away, player,
                                                                  goals=0, shots=3, xg=0.5, xa=0.1, source_rating=7.2),),
    )


@pytest.fixture
def pair():
    return (dataset("espn", "1", "cup", "10", "20", "101"),
            dataset("scores365", "2", "72", "30", "40", "201"))


@pytest.fixture
def identities():
    return esd.IdentityMap([
        esd.EntityAlias(kind, canonical, source, native)
        for kind, canonical, natives in (("competition", "cup", ("cup", "72")), ("team", "home", ("10", "30")),
                                         ("team", "away", ("20", "40")), ("player", "player", ("101", "201")))
        for source, native in zip(("espn", "scores365"), natives)
    ])


def lineup(dataset, **changes):
    return replace(dataset, lineup_records=(replace(dataset.lineup_records[0], **changes),))


def stats(dataset, **changes):
    return replace(dataset, player_match_stat_records=(replace(dataset.player_match_stat_records[0], **changes),))


def test_scoped_players_use_native_team_and_original_kickoff(pair, identities):
    aliases = esd.IdentityMap(replace(alias, team_id="20" if alias.source == "espn" else "40",
                                      valid_from=NOW, valid_until=NOW + timedelta(days=1),
                                      source_url="https://example.com/review", verified_at=NOW)
                              if alias.kind == "player" else alias for alias in identities.aliases)
    report = esd.compare_match_players(*pair, identities=aliases)
    assert len(report.rows) == 1 and not report.unresolved
    assert report.identity_aliases == aliases.aliases
    invalid = lineup(pair[1], team_id="30", home_away="home")
    invalid = stats(invalid, team_id="30")
    report = esd.compare_match_players(pair[0], invalid, identities=aliases)
    assert any(row.reason == "player_identity_out_of_scope" for row in report.unresolved)
    expired = esd.IdentityMap(replace(alias, valid_until=NOW, valid_from=NOW - timedelta(days=1))
                             if alias.kind == "player" else alias for alias in aliases.aliases)
    report = esd.compare_match_players(*pair, identities=expired)
    assert all(row.reason == "player_identity_out_of_scope" for row in report.unresolved)


def test_validity_uses_each_native_kickoff_even_when_matches_link_with_tolerance(pair, identities):
    aliases = esd.IdentityMap(replace(alias, valid_until=NOW + timedelta(seconds=1))
                              if alias.kind == "player" else alias for alias in identities.aliases)
    right = replace(pair[1], match_records=(replace(pair[1].match_records[0], kickoff=NOW + timedelta(seconds=2)),))
    report = esd.compare_match_players(pair[0], right, identities=aliases)
    assert len(report.linkage.links) == 1
    assert any(row.right_lineup is not None and row.reason == "player_identity_out_of_scope" for row in report.unresolved)


def test_unique_player_links_retain_records_and_unknown_flags(pair, identities):
    report = esd.compare_match_players(*pair, identities=identities, metrics=["goals", "minutes"])
    row, = report.rows
    assert row.status == "equal" and not report.differences and not report.unresolved
    assert row.left_lineup is pair[0].lineup_records[0] and row.right_statistics is pair[1].player_match_stat_records[0]
    assert set(row.unknown_fields) == {"captain", "position", "formation", "confirmed"}
    assert report.statistics[0].status == "equal" and report.statistics[0].delta == 0
    assert report.statistics[1].status == "missing_both" and report.statistics[1].delta is None
    assert report.left_coverage[0].successful and report.left_coverage[0].lineup_count == 1
    assert row.left_fetched_at == row.right_fetched_at == NOW
    with pytest.raises(FrozenInstanceError):
        row.status = "other"


@pytest.mark.parametrize("changes,field", [({"starter": True}, "starter"), ({"jersey_number": "1"}, "jersey_number"),
                                         ({"captain": True}, "captain"), ({"formation": "4-3-3"}, "formation")])
def test_known_lineup_differences(pair, identities, changes, field):
    left = lineup(pair[0], captain=False, formation="4-4-2")
    report = esd.compare_match_players(left, lineup(pair[1], **changes), identities=identities)
    assert field in report.rows[0].differences and report.rows[0] in report.differences


def test_team_difference_is_an_observation_not_a_player_identity(pair, identities):
    right = lineup(pair[1], team_id="30", home_away="home")
    right = stats(right, team_id="30")
    report = esd.compare_match_players(pair[0], right, identities=identities)
    assert report.rows[0].differences == ("team_id", "home_away")
    assert not report.unresolved


def test_position_labels_require_explicit_cross_source_aliases(pair, identities):
    row, = esd.compare_match_players(*pair, identities=identities).rows
    assert "position" in row.unknown_fields  # Identical source labels do not establish equivalence.
    aliases = {("espn", "MID"): "midfielder", ("scores365", "MID"): "midfielder"}
    report = esd.compare_match_players(*pair, identities=identities, position_aliases=aliases)
    assert "position" not in report.rows[0].unknown_fields
    aliases["scores365", "MID"] = "forward"
    assert "position" in esd.compare_match_players(*pair, identities=identities, position_aliases=aliases).rows[0].differences


def test_same_source_uses_native_ids_and_positions_without_aliases(pair):
    report = esd.compare_match_players(pair[0], stats(lineup(pair[0], starter=True), shots=4))
    assert report.rows[0].differences == ("starter",)
    assert "position" not in report.rows[0].unknown_fields
    assert any(row.metric == "shots" and row.delta == 1 for row in report.statistic_differences)
    assert next(row for row in report.statistics if row.metric == "xg").status == "equal"


def test_names_jerseys_and_athlete_ids_never_link_players(pair, identities):
    mapping = esd.IdentityMap(alias for alias in identities.aliases if alias.kind != "player")
    mapping = mapping.with_aliases([esd.EntityAlias("player", "p", "espn", "101"), esd.EntityAlias("player", "p", "scores365", "999")])
    report = esd.compare_match_players(pair[0], lineup(pair[1], source_athlete_id="999"), identities=mapping)
    assert len(report.unresolved) == 2
    assert report.rows[1].reason == "player_identity_unknown"
    assert all(row.delta is None for row in report.statistics)


def test_many_to_one_aliases_are_ambiguous_in_both_directions(pair, identities):
    left = replace(pair[0], lineup_records=(*pair[0].lineup_records, replace(pair[0].lineup_records[0], player_id="102")))
    mapping = identities.with_aliases([esd.EntityAlias("player", "player", "espn", "102")])
    report = esd.compare_match_players(left, pair[1], identities=mapping)
    assert len(report.rows) == 3 and len(report.unresolved) == 3
    assert all(row.status.startswith("ambiguous_") for row in report.rows)
    assert report.rows[-1].candidate_keys == ("101", "102")
    assert report.rows[0].left_statistics is left.player_match_stat_records[0]


def test_duplicate_alias_without_opposite_candidate_remains_ambiguous(pair, identities):
    left = replace(pair[0], lineup_records=(*pair[0].lineup_records, replace(pair[0].lineup_records[0], player_id="102")))
    mapping = esd.IdentityMap(alias for alias in identities.aliases if alias.kind != "player").with_aliases([
        esd.EntityAlias("player", "p", "espn", native) for native in ("101", "102")])
    report = esd.compare_match_players(left, pair[1], identities=mapping)
    assert report.rows[0].status == "ambiguous_left" and report.rows[0].candidate_keys == ()


@pytest.mark.parametrize("metric", ["xg", "xa", "source_rating"])
def test_cross_source_models_have_no_delta_even_if_identical(pair, identities, metric):
    report = esd.compare_match_players(*pair, identities=identities, metrics=[metric], tolerances={metric: 100})
    row, = report.statistics
    assert row.status == "source_specific" and row.delta is None
    assert report.unresolved_statistics == (row,)


def test_missing_minutes_are_not_zero_and_tolerances_retain_differences(pair, identities):
    right = stats(pair[1], minutes=0, shots=4)
    report = esd.compare_match_players(pair[0], right, identities=identities,
                                       metrics=["minutes", "shots"], tolerances={"shots": 1})
    assert report.statistics[0].status == "missing_left" and report.statistics[0].left_value is None
    assert report.statistics[1].status == "equal" and report.statistics[1].delta == 1
    assert not report.statistic_differences
    assert esd.compare_match_players(pair[0], right, identities=identities, metrics=["shots"]).statistic_differences[0].delta == 1


def test_same_source_decimal_tolerance_avoids_binary_boundary_error(pair):
    report = esd.compare_match_players(stats(pair[0], xg=0.5), stats(pair[0], xg=0.6), metrics=["xg"], tolerances={"xg": 0.1})
    assert report.statistics[0].status == "equal" and report.statistics[0].delta == 0.1


@pytest.mark.parametrize("side", [0, 1])
def test_unselected_statistics_differ_from_missing_records(pair, identities, side):
    values = list(pair)
    values[side] = replace(values[side], metadata=replace(values[side].metadata, tables=("matches", "lineups")), player_match_stat_records=())
    row, = esd.compare_match_players(*values, identities=identities, metrics=["goals"]).statistics
    assert row.status == f"table_unselected_{'left' if side == 0 else 'right'}" and row.delta is None
    no_stats = tuple(replace(item, metadata=replace(item.metadata, tables=("matches", "lineups")), player_match_stat_records=()) for item in pair)
    assert esd.compare_match_players(*no_stats, identities=identities).statistics == ()


def test_missing_record_differs_from_null_metric(pair, identities):
    report = esd.compare_match_players(replace(pair[0], player_match_stat_records=()), pair[1], identities=identities, metrics=["goals"])
    assert report.statistics[0].status == "record_missing_left"
    assert report.rows[0].status == "equal"  # Lineup comparison is independent.


def test_successful_empty_vs_failed_player_request_and_original_provenance(pair, identities):
    empty = replace(pair[1], lineup_records=(), player_match_stat_records=())
    report = esd.compare_match_players(pair[0], empty, identities=identities)
    assert report.right_coverage[0].successful and report.right_coverage[0].lineup_count == 0
    assert report.unresolved[0].status == "unmatched_left"
    failed = replace(empty, errors=(esd.DatasetIssue("lineups", "2", "SourceBlocked", "Blocked"),),
                     metadata=replace(empty.metadata, successful_tasks=(), response_fetched_at=(("context:2", NOW.isoformat()),)))
    report = esd.compare_match_players(pair[0], failed, identities=identities)
    assert not report.right_complete and not report.right_coverage[0].successful
    assert report.right_errors == failed.errors and report.rows[0].right_fetched_at is None
    newer = replace(pair[1], metadata=replace(pair[1].metadata, finished_at=NOW + timedelta(days=1), cached_tasks=("lineups:2",)))
    assert esd.compare_match_players(pair[0], newer, identities=identities).rows[0].right_fetched_at == NOW


def test_unlinked_or_ambiguous_fixtures_keep_all_listed_players(pair, identities):
    right = replace(pair[1], match_records=(replace(pair[1].match_records[0], kickoff=NOW + timedelta(hours=1)),))
    report = esd.compare_match_players(pair[0], right, identities=identities)
    assert len(report.rows) == 2 and all(row.reason == "match_unlinked" for row in report.rows)
    other_match = replace(pair[1].match_records[0], match_id="3")
    right = replace(pair[1], match_records=(*pair[1].match_records, other_match))
    report = esd.compare_match_players(pair[0], right, identities=identities)
    assert len(report.rows) == 2 and all(row.reason == "match_ambiguous" for row in report.rows)


@pytest.mark.parametrize("options", [{"metrics": "goals"}, {"metrics": []}, {"metrics": ["unknown"]},
    {"tolerances": []}, {"tolerances": {"goals": True}}, {"tolerances": {"goals": -1}},
    {"tolerances": {"goals": float("nan")}}, {"metrics": ["goals"], "tolerances": {"shots": 1}},
    {"position_aliases": []}, {"position_aliases": {"MID": "midfield"}},
    {"position_aliases": {("espn", "MID"): None}}, {"tolerance_seconds": True}, {"tolerance_seconds": "300"}])
def test_invalid_comparison_settings(pair, options):
    with pytest.raises(ValueError):
        esd.compare_match_players(*pair, **options)


def test_invalid_datasets_and_orphan_statistics_are_rejected(pair, identities):
    with pytest.raises(TypeError):
        esd.compare_match_players(None, pair[1])
    with pytest.raises(ValueError, match="lineup records"):
        esd.compare_match_players(replace(pair[0], lineup_records=()), pair[1], identities=identities)
    with pytest.raises(ValueError, match="matching native match IDs"):
        esd.compare_match_players(replace(pair[0], match_records=()), pair[1], identities=identities)
    with pytest.raises(ValueError, match="Invalid player dataset"):
        esd.compare_match_players(stats(pair[0], goals=-1), pair[1], identities=identities)
    no_lineups = replace(pair[0], metadata=replace(pair[0].metadata, tables=("matches",)), lineup_records=(), player_match_stat_records=())
    with pytest.raises(ValueError, match="select matches and lineups"):
        esd.compare_match_players(no_lineups, pair[1], identities=identities)
    unsupported = replace(no_lineups, metadata=replace(no_lineups.metadata, source="understat"),
                          match_records=(replace(no_lineups.match_records[0], source="understat"),))
    with pytest.raises(ValueError, match="supports ESPN, 365Scores and Sofascore"):
        esd.compare_match_players(unsupported, pair[1], identities=identities)


def test_base_comparison_does_not_import_optional_dependencies(pair, identities):
    original = builtins.__import__

    def guarded(name, *args, **kwargs):
        if name.split(".")[0] in ("pandas", "pyarrow"):
            raise ModuleNotFoundError(f"Blocked {name}", name=name.split(".")[0])
        return original(name, *args, **kwargs)

    with patch("builtins.__import__", guarded):
        report = esd.compare_match_players(*pair, identities=identities)
        for table in ("lineups", "statistics"):
            with pytest.raises(ImportError, match=r"EasySoccerData\[pandas\]"):
                report.to_dataframe(table)


def test_fixed_nullable_dataframes_and_snapshot_roundtrip(pair, identities, tmp_path):
    pytest.importorskip("pandas")
    report = esd.compare_match_players(*pair, identities=identities, metrics=["goals", "minutes"])
    frame = report.to_dataframe()
    assert str(frame.left_player_id.dtype) == "string" and frame.left_player_id.iloc[0] == "101"
    assert str(frame.left_starter.dtype) == "boolean" and not frame.left_starter.iloc[0]
    assert frame.left_jersey_number.iloc[0] == "01" and frame.left_confirmed.isna().all()
    assert str(frame.left_fetched_at.dtype) == "datetime64[ns, UTC]"
    values = report.to_dataframe("statistics")
    assert str(values.left_value.dtype) == "Float64" and values.delta.isna().sum() == 1
    assert values.attrs == {"report": "match_players", "report_table": "statistics", "report_version": "1"}
    empty = tuple(replace(item, lineup_records=(), player_match_stat_records=()) for item in pair)
    blank = esd.compare_match_players(*empty, identities=identities)
    for table in ("lineups", "statistics"):
        assert list(blank.to_dataframe(table).columns) == list(report.to_dataframe(table).columns)
        assert blank.to_dataframe(table).dtypes.equals(report.to_dataframe(table).dtypes)
    with pytest.raises(ValueError):
        report.to_dataframe("unknown")
    pytest.importorskip("pyarrow")
    restored = tuple(esd.open_dataset(item.save(tmp_path / item.metadata.source)) for item in pair)
    assert esd.compare_match_players(*restored, identities=identities, metrics=["goals", "minutes"]) == report

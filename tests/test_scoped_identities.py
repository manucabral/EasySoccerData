"""Player aliases require reviewed context, with half-open validity windows."""

import json
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone

import pytest

import esd

NOW = datetime(2026, 11, 3, 20, tzinfo=timezone.utc)


def alias(**changes):
    return replace(esd.EntityAlias("player", "person", "espn", "001", team_id="010",
                                   valid_from=NOW, valid_until=NOW + timedelta(days=1),
                                   source_url="https://example.com/roster", verified_at=NOW), **changes)


def test_required_context_and_exclusive_upper_boundary():
    identities = esd.IdentityMap([alias()])
    assert identities.lookup("player", "espn", "001").status == "context_required"
    assert identities.lookup("player", "espn", "001", team_id="010").status == "context_required"
    assert identities.resolve("player", "espn", "001", team_id="010", at=NOW) == "person"
    for team, at in (("011", NOW), ("010", NOW - timedelta(seconds=1)), ("010", NOW + timedelta(days=1))):
        result = identities.lookup("player", "espn", "001", team_id=team, at=at)
        assert result.status == "out_of_scope" and result.canonical_id is None
    assert identities.lookup("player", "espn", "unknown").status == "unmapped"
    assert identities.resolve("team", "espn", "001", team_id="010", at=NOW) is None
    assert identities.resolve("player", "scores365", "001", team_id="010", at=NOW) is None


def test_reused_native_id_can_resolve_to_different_people_in_disjoint_scopes():
    old = alias(valid_until=NOW + timedelta(days=1))
    new = alias(canonical_id="another", valid_from=old.valid_until, valid_until=None)
    other_team = alias(canonical_id="third", team_id="020")
    identities = esd.IdentityMap([old, new, other_team])
    assert identities.resolve("player", "espn", "001", team_id="010", at=NOW) == "person"
    assert identities.resolve("player", "espn", "001", team_id="010", at=new.valid_from) == "another"
    assert identities.resolve("player", "espn", "001", team_id="020", at=NOW) == "third"
    assert identities.resolve("player", "espn", "001", at=NOW) is None
    with pytest.raises(ValueError, match="Conflicting"):
        identities.with_aliases([alias(canonical_id="conflicting")])
    with pytest.raises(ValueError, match="Conflicting"):
        identities.with_aliases([esd.EntityAlias("player", "global-conflict", "espn", "001")])


def test_transfer_keeps_one_person_across_native_teams():
    first = alias(valid_until=NOW)
    first = replace(first, valid_from=NOW - timedelta(days=30))
    second = alias(team_id="020", valid_until=None)
    identities = esd.IdentityMap([first, second, second])
    assert len(identities.aliases) == 2
    assert identities.resolve("player", "espn", "001", team_id="020", at=NOW) == "person"
    assert identities.resolve("player", "espn", "001", team_id="010", at=NOW) is None
    result = identities.lookup("player", "espn", "001", team_id="020", at=NOW)
    assert result.aliases == (second,)
    with pytest.raises(FrozenInstanceError):
        result.status = "changed"


def test_json_roundtrip_preserves_scope_review_and_old_four_field_lists():
    identities = esd.IdentityMap([alias()])
    document = json.loads(json.dumps(identities.to_dict()))
    document["aliases"][0]["valid_from"] = "2026-11-03T20:00:00Z"
    restored = esd.IdentityMap.from_dict(document)
    assert restored.aliases == identities.aliases
    assert restored.resolve("player", "espn", "001", team_id="010", at=NOW) == "person"
    assert esd.IdentityMap.from_dict([{"kind": "player", "canonical_id": "p", "source": "espn", "source_id": "001"}]).resolve("player", "espn", "001") == "p"
    assert esd.IdentityMap(restored.aliases).aliases == restored.aliases


@pytest.mark.parametrize("change", [
    {"kind": "team"}, {"team_id": " "}, {"team_id": 10}, {"valid_from": NOW.replace(tzinfo=None)},
    {"valid_until": NOW}, {"verified_at": "yesterday"}, {"source_url": "file:///local"},
    {"source_url": "https://user:secret@example.com"},
])
def test_malformed_scope_and_evidence_are_rejected(change):
    with pytest.raises(ValueError):
        esd.IdentityMap([alias(**change)])


@pytest.mark.parametrize("data", [{}, {"format": "easysoccerdata-identities", "format_version": True, "aliases": []},
                                  [{"unexpected": 1}], [{"kind": "player", "valid_from": "yesterday"}], "aliases"])
def test_invalid_identity_documents_are_rejected(data):
    with pytest.raises(ValueError):
        esd.IdentityMap.from_dict(data)

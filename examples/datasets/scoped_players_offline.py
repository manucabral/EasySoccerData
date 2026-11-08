"""Artificial reviewed player scopes and JSON roundtrip, without HTTP or extras."""

import json
from datetime import datetime, timezone

import esd


def main():
    boundary = datetime(2026, 7, 1, tzinfo=timezone.utc)
    aliases = esd.IdentityMap([
        esd.EntityAlias("player", "example-person", "espn", "001", team_id="old-team", valid_until=boundary),
        esd.EntityAlias("player", "example-person", "espn", "001", team_id="new-team", valid_from=boundary),
        esd.EntityAlias("player", "example-person", "scores365", "002", team_id="other-native-team", valid_from=boundary),
    ])
    assert aliases.lookup("player", "espn", "001").status == "context_required"
    assert aliases.lookup("player", "espn", "001", team_id="old-team", at=boundary).status == "out_of_scope"
    assert aliases.resolve("player", "espn", "001", team_id="new-team", at=boundary) == "example-person"
    document = json.loads(json.dumps(aliases.to_dict()))
    restored = esd.IdentityMap.from_dict(document)
    assert restored.aliases == aliases.aliases
    print("Artificial transfer boundary: start inclusive, end exclusive, native IDs retained")
    for team in (None, "old-team", "new-team"):
        result = restored.lookup("player", "espn", "001", team_id=team, at=boundary)
        print("Native team:", team, "| Decision:", result.status, "| Canonical identity:", result.canonical_id)


if __name__ == "__main__":
    main()

"""Offline artificial records showing explicit identities and match linkage."""

from dataclasses import replace
from datetime import datetime, timezone

import esd


def sample(source, league, match_id, home_id, away_id):
    timestamp = datetime(2024, 8, 16, 19, tzinfo=timezone.utc)
    return esd.SoccerDataset(
        metadata=esd.DatasetMetadata(
            source,
            league,
            2024,
            ("matches",),
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
                kickoff=timestamp,
                home_team_id=home_id,
                away_team_id=away_id,
            ),
        ),
    )


def main():
    # These are artificial IDs, not a catalogue of real-world equivalences.
    left = sample("espn", "example-league-a", "native-match-a", "native-home-a", "native-away-a")
    right = sample(
        "understat", "example-league-b", "native-match-b", "native-home-b", "native-away-b"
    )
    identities = esd.IdentityMap(
        [
            esd.EntityAlias("competition", "example-league", "espn", "example-league-a"),
            esd.EntityAlias("competition", "example-league", "understat", "example-league-b"),
            esd.EntityAlias("team", "example-home", "espn", "native-home-a"),
            esd.EntityAlias("team", "example-home", "understat", "native-home-b"),
            esd.EntityAlias("team", "example-away", "espn", "native-away-a"),
            esd.EntityAlias("team", "example-away", "understat", "native-away-b"),
        ]
    )
    report = esd.check_dataset_compatibility(left, right, identities=identities)
    print("Schema:", report.schema_compatible, "Identities:", report.identity_compatible)
    result = esd.link_dataset_matches(left, right, identities=identities)
    for link in result.links:
        print(link.left_source, link.left_match_id, "->", link.right_source, link.right_match_id)
    print("Unmatched:", result.unmatched_left, result.unmatched_right)
    print("Ambiguous:", result.ambiguous_left, result.ambiguous_right)
    # Two candidates are reported, rather than selecting one arbitrarily.
    duplicate = replace(right.match_records[0], match_id="second-candidate")
    ambiguous = esd.link_dataset_matches(
        left,
        replace(right, match_records=(*right.match_records, duplicate)),
        identities=identities,
    )
    assert not ambiguous.links and ambiguous.ambiguous_left and ambiguous.ambiguous_right
    print("Two candidates:", ambiguous.ambiguous_left, ambiguous.ambiguous_right)


if __name__ == "__main__":
    main()

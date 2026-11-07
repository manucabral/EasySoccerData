"""Offline smoke checks for an installed wheel and its optional dependencies."""

import argparse
import importlib.util
import sys
from datetime import datetime, timezone
from importlib.metadata import metadata
from pathlib import Path
from tempfile import TemporaryDirectory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extra", choices=("base", "pandas", "parquet", "full"), required=True)
    args = parser.parse_args()
    wants_pandas = args.extra in ("pandas", "full")
    wants_arrow = args.extra in ("parquet", "full")
    assert (importlib.util.find_spec("pandas") is not None) == wants_pandas
    assert (importlib.util.find_spec("pyarrow") is not None) == wants_arrow

    import esd

    assert "site-packages" in Path(esd.__file__).parts, esd.__file__
    assert metadata("EasySoccerData")["License-Expression"] == "MIT"
    assert "pandas" not in sys.modules and "pyarrow" not in sys.modules
    assert len(esd.get_dataset_capabilities()) == 9
    assert all(contract.tables for contract in esd.get_dataset_capabilities().values())
    now = datetime(2024, 8, 16, 19, tzinfo=timezone.utc)
    dataset = esd.SoccerDataset(
        esd.DatasetMetadata(
            "espn",
            "eng.1",
            2024,
            ("matches",),
            now,
            now,
            expected_tasks=("matches:1",),
            successful_tasks=("matches:1",),
        ),
        match_records=(
            esd.NormalizedMatch(
                "espn",
                match_id="1",
                competition_id="eng.1",
                home_team_id="10",
                away_team_id="20",
                kickoff=now,
                home_score=0,
                away_score=None,
            ),
        ),
    )
    assert esd.link_dataset_matches(dataset, dataset).links
    with TemporaryDirectory(prefix="esd-install-") as directory:
        cache = esd.ResponseCache(Path(directory) / "cache")
        cache.set("query", {"events": []})
        assert cache.get("query", ttl=60).data == {"events": []}
        if wants_arrow:
            assert esd.open_dataset(dataset.save(Path(directory) / "snapshot")) == dataset
        else:
            try:
                dataset.save(Path(directory) / "snapshot")
            except ImportError as exc:
                assert "EasySoccerData[parquet]" in str(exc)
            else:
                raise AssertionError("Saving without PyArrow must fail")
    if wants_pandas:
        frame = dataset.matches
        assert str(frame.home_score.dtype) == "Int64"
        assert str(frame.kickoff.dtype) == "datetime64[ns, UTC]"
        assert frame.home_score.iloc[0] == 0
        assert frame.away_score.isna().all()
    else:
        assert "pandas" not in sys.modules
        try:
            _ = dataset.matches
        except ImportError as exc:
            assert "EasySoccerData[pandas]" in str(exc)
        else:
            raise AssertionError("DataFrames without pandas must fail")
    print(f"Python {sys.version.split()[0]}: installed {args.extra} passed ({esd.__file__})")


if __name__ == "__main__":
    main()

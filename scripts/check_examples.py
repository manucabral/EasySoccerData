"""Run documented offline examples with the selected installation extra."""

import argparse
import subprocess
import sys
from pathlib import Path

BASE = (
    ("examples/datasets/catalog.py", "--list"),
    ("examples/datasets/catalog_workflow_offline.py",),
    ("examples/datasets/match_players.py", "--help"),
    ("examples/datasets/match_players_offline.py",),
    ("examples/datasets/champions_statistics.py", "--help"),
    ("examples/datasets/compare_statistics_offline.py",),
    ("examples/datasets/match_statistics.py", "--help"),
    ("examples/datasets/match_statistics_offline.py",),
    ("examples/datasets/discover_and_download.py", "--help"),
    ("examples/datasets/discovery_workflow_offline.py",),
    ("examples/datasets/discovery_offline.py",),
    ("examples/datasets/discover.py", "--list"),
    ("examples/datasets/validate_dataset.py",),
    ("examples/datasets/providers.py", "--list"),
    ("examples/pandas/champions_analysis.py", "--help"),
    ("examples/datasets/champions_compare.py", "--help"),
    ("examples/datasets/link_matches.py",),
    ("examples/datasets/partial_results.py",),
    ("examples/datasets/cache_resume_offline.py",),
)
PANDAS = (
    ("examples/datasets/catalog_workflow_offline.py", "--pandas"),
    ("examples/datasets/match_players_offline.py", "--pandas"),
    ("examples/datasets/compare_statistics_offline.py", "--pandas"),
    ("examples/datasets/match_statistics_offline.py", "--pandas"),
    ("examples/pandas/matches_and_standings.py",),
    ("examples/pandas/normalized_tables.py",),
    ("examples/pandas/dataset_analysis.py",),
)
PARQUET = (("examples/datasets/parquet_roundtrip.py",),
           ("examples/datasets/catalog_workflow_offline.py", "--parquet"),
           ("examples/datasets/match_players_offline.py", "--parquet"),
           ("examples/datasets/compare_statistics_offline.py", "--parquet"),
           ("examples/datasets/discovery_workflow_offline.py", "--parquet"),
           ("examples/datasets/match_statistics_offline.py", "--parquet"))

WRAPPER = """
import runpy
import sys
from pathlib import Path
from unittest.mock import patch

def no_network(*args, **kwargs):
    raise AssertionError("Offline example attempted HTTP or browser access")

sys.argv = sys.argv[1:]
root, mode = Path(sys.argv.pop(0)).resolve(), sys.argv.pop(0)
if mode == "installed":
    sys.path = [entry for entry in sys.path if Path(entry or ".").resolve() != root]
    import esd
    if "site-packages" not in Path(esd.__file__).parts or Path(esd.__file__).resolve().is_relative_to(root / "esd"):
        raise AssertionError(f"Expected installed wheel, imported {esd.__file__}")
with patch("httpx.Client.request", no_network), \\
     patch("curl_cffi.requests.Session.request", no_network), \\
     patch("esd.utils.BrowserSession._launch", no_network):
    runpy.run_path(sys.argv[0], run_name="__main__")
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extra", choices=("base", "pandas", "parquet", "full"), default="base")
    parser.add_argument("--installed", action="store_true", help="Require the installed package and exclude the checkout from imports")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    cases = [*BASE]
    if args.extra in ("pandas", "full"):
        cases.extend(PANDAS)
    if args.extra in ("parquet", "full"):
        cases.extend(PARQUET)
    for path, *arguments in cases:
        result = subprocess.run(
            [sys.executable, "-c", WRAPPER, str(root), "installed" if args.installed else "source", str(root / path), *arguments],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if result.returncode:
            raise RuntimeError(f"Example failed: {path}\n{result.stdout}\n{result.stderr}")
        print("Passed:", path)
    print(f"{len(cases)} offline examples passed ({args.extra})")


if __name__ == "__main__":
    main()

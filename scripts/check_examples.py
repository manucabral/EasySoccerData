"""Run documented offline examples with the selected installation extra."""

import argparse
import subprocess
import sys
from pathlib import Path

BASE = (
    ("examples/datasets/providers.py", "--list"),
    ("examples/datasets/link_matches.py",),
    ("examples/datasets/partial_results.py",),
    ("examples/datasets/cache_resume_offline.py",),
)
PANDAS = (
    ("examples/pandas/matches_and_standings.py",),
    ("examples/pandas/normalized_tables.py",),
    ("examples/pandas/dataset_analysis.py",),
)
PARQUET = (("examples/datasets/parquet_roundtrip.py",),)

WRAPPER = """
import runpy
import sys
from unittest.mock import patch

def no_network(*args, **kwargs):
    raise AssertionError("Offline example attempted HTTP or browser access")

sys.argv = sys.argv[1:]
with patch("httpx.Client.request", no_network), \\
     patch("curl_cffi.requests.Session.request", no_network), \\
     patch("esd.utils.BrowserSession._launch", no_network):
    runpy.run_path(sys.argv[0], run_name="__main__")
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extra", choices=("base", "pandas", "parquet", "full"), default="base")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    cases = [*BASE]
    if args.extra in ("pandas", "full"):
        cases.extend(PANDAS)
    if args.extra in ("parquet", "full"):
        cases.extend(PARQUET)
    for path, *arguments in cases:
        result = subprocess.run(
            [sys.executable, "-c", WRAPPER, str(root / path), *arguments],
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

"""Example checks distinguish a checkout from a wheel in an in-project venv."""

import os
import runpy
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize("mode,expected", [("source", "checkout"), ("installed", "wheel")])
def test_wrapper_imports_the_requested_package_location(tmp_path, mode, expected):
    root = tmp_path / "checkout"
    site_packages = root / "install-env" / "Lib" / "site-packages"
    for base, label in ((root, "checkout"), (site_packages, "wheel")):
        package = base / "esd"
        package.mkdir(parents=True)
        (package / "__init__.py").write_text(f"LOCATION = {label!r}\n", encoding="utf-8")
        (package / "utils.py").write_text("class BrowserSession:\n    def _launch(self): pass\n", encoding="utf-8")
    example = root / "example.py"
    example.write_text("import esd\nprint(esd.LOCATION)\n", encoding="utf-8")
    runner = Path(__file__).resolve().parent.parent / "scripts/check_examples.py"
    wrapper = runpy.run_path(str(runner))["WRAPPER"]
    environment = dict(os.environ, PYTHONPATH=str(site_packages))
    result = subprocess.run([sys.executable, "-c", wrapper, str(root), mode, str(example)],
                            cwd=root, env=environment, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == expected

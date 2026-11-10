"""Real-browser checks: forms, chat widget, live demo and phone layout.

Runs tests/browser/smoke.cjs with Node + Playwright (Chromium). All backend
calls are intercepted and faked inside the browser, so nothing external is hit.
Skipped automatically if Node's Playwright isn't installed.
"""
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from conftest import TEST_ENV

SCRIPT = Path(__file__).parent / "browser" / "smoke.cjs"


def _playwright_available():
    if not shutil.which("node"):
        return False
    return subprocess.run(["node", "-e", "require('playwright')"], capture_output=True).returncode == 0


@pytest.fixture(scope="module")
def browser_results(built_site):
    if not _playwright_available():
        pytest.skip("Node Playwright not installed")
    out = subprocess.run(
        ["node", str(SCRIPT)], env={**os.environ, **TEST_ENV}, capture_output=True, text=True, timeout=180
    )
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout.strip().splitlines()[-1])


@pytest.mark.parametrize("name", [
    "preview form sends lead",
    "preview form rejects non-maps link",
    "preview form shows error when backend fails",
    "spam bots are ignored",
    "waitlist form sends signup",
    "chat widget answers as Prezence",
    "chat widget shows friendly error when offline",
    "chat messages are shown as text, not HTML",
    "live demo opens chat for demo business",
    "no sideways scrolling on a small phone",
])
def test_in_browser(browser_results, name):
    assert browser_results.get(name) == "ok", browser_results.get(name, "check did not run")

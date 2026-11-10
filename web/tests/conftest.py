"""Shared test setup for the website.

The tests build the static site once (npm run build) and then read the HTML
files in dist/. No external services are called: the site is static, and the
form/chat only talk to the backend from a real browser.

Set SKIP_BUILD=1 to reuse an existing dist/ folder (faster while editing tests).
"""
import json
import os
import subprocess
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

WEB_DIR = Path(__file__).resolve().parent.parent
DIST = WEB_DIR / "dist"
DATA = WEB_DIR / "src" / "data"

# Fixed, fake settings so test results don't depend on anyone's .env file.
TEST_ENV = {
    "PUBLIC_SITE_URL": "https://test.prezence.example",
    "PUBLIC_API_URL": "https://api.test.example",
    "PUBLIC_DEMO_PHONE": "+1 (555) 010-0199",
    "PUBLIC_CONTACT_EMAIL": "hello@test.example",
}


@pytest.fixture(scope="session", autouse=True)
def built_site():
    """Build the site once for the whole test run."""
    if os.environ.get("SKIP_BUILD") != "1":
        result = subprocess.run(
            ["npm", "run", "build"],
            cwd=WEB_DIR,
            env={**os.environ, **TEST_ENV},
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr
    return DIST


def load_data(name):
    """Read one of the JSON files in src/data."""
    return json.loads((DATA / name).read_text())


def page_path(url_path):
    """Map a URL like '/pricing' to its built file 'dist/pricing/index.html'."""
    url_path = url_path.strip("/")
    return DIST / url_path / "index.html" if url_path else DIST / "index.html"


@pytest.fixture
def page():
    """Usage in a test: soup = page('/pricing')"""
    def _load(url_path):
        path = page_path(url_path)
        assert path.exists(), f"page not built: {url_path}"
        return BeautifulSoup(path.read_text(), "html.parser")
    return _load

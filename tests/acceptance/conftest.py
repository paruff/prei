"""Shared fixtures for HTTP acceptance tests.

Tests make real HTTP requests — either to a deployed application (local
Docker container, staging URL, or production URL via ``BASE_URL``), or,
when ``BASE_URL`` isn't set, to a pytest-django ``live_server`` started
for the test session. No Django test client either way.
"""

from __future__ import annotations

import os

import httpx
import pytest


@pytest.fixture(scope="session")
def base_url(request: pytest.FixtureRequest) -> str:
    """Base URL to run acceptance tests against.

    Set via ``BASE_URL`` environment variable to target a deployed
    artifact (local Docker container, staging, production — the
    ``post-deployment.yml``/``make test-acceptance`` path). When unset
    (the PR-gate path), falls back to a ``live_server`` spun up for
    this test session against a freshly-migrated database — lazily
    requested so runs that already have ``BASE_URL`` never touch
    Django's DB fixtures at all.
    """
    env_url = os.environ.get("BASE_URL")
    if env_url:
        return env_url
    request.getfixturevalue("django_db_setup")
    live_server = request.getfixturevalue("live_server")
    return live_server.url


@pytest.fixture(autouse=True)
def _enable_db_for_live_server(request: pytest.FixtureRequest, base_url: str) -> None:
    """Unblock DB access when running against the live_server fallback.

    pytest-django blocks DB access per test function unless that test
    requested it; the live server handles requests on a background
    thread that inherits the block. Only needed when ``BASE_URL`` isn't
    set — deployed-artifact runs never touch Django's DB fixtures.
    """
    if not os.environ.get("BASE_URL"):
        request.getfixturevalue("db")


@pytest.fixture(scope="session")
def client(base_url: str) -> httpx.Client:
    """Pre-configured httpx client with base URL and 30-second timeout."""
    return httpx.Client(base_url=base_url, timeout=30, follow_redirects=False)

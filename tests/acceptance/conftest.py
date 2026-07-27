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


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Mark every acceptance test as needing DB access, live_server-fallback only.

    pytest-django decides which database aliases to migrate by statically
    scanning each collected test's declared fixture names / ``django_db``
    marker (see ``_get_databases_for_test`` in pytest-django) — a scan that
    happens before any fixture body runs. Our ``client``/``base_url``
    fixtures only reach ``db``/``live_server`` dynamically, via
    ``request.getfixturevalue()`` inside the fixture body, which that static
    scan can't see. Without this marker pytest-django concludes no test
    needs a database, skips ``migrate`` entirely, and every request 500s
    with "no such table". ``transaction=True`` matches ``live_server``'s
    own dependency on ``transactional_db`` (required so writes made on the
    main thread are visible to the live_server's background-thread
    connection). Skipped when ``BASE_URL`` is set — deployed-artifact runs
    never touch Django's DB fixtures.
    """
    if os.environ.get("BASE_URL"):
        return
    for item in items:
        item.add_marker(pytest.mark.django_db(transaction=True))


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


@pytest.fixture(scope="session")
def client(base_url: str) -> httpx.Client:
    """Pre-configured httpx client with base URL and 30-second timeout."""
    return httpx.Client(base_url=base_url, timeout=30, follow_redirects=False)

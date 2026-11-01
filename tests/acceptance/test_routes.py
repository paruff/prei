"""Route smoke test: every named GET route answers non-5xx for the demo user (AC-16).

Runs over HTTP against ``BASE_URL`` (the seeded container, ``make docker-accept``).
Routes are read from ``core.urls`` so a new route is covered without editing this file.
"""

from __future__ import annotations

import os
import re

import httpx
import pytest
from core.urls import urlpatterns

pytestmark = pytest.mark.acceptance

DEMO = {"username": "demo", "password": "DemoPass123!"}  # noqa: S105 - seed demo user
# GET starts a refresh against external sources, or deletes: not safe to smoke-test.
SKIP_NAMES = {
    "refresh_all_sources",
    "update_market_indicators",
    "market_refresh",
    "property_delete",
    "pipeline_kill",
}
PARAM = re.compile(r"<int:\w+>")


@pytest.fixture(scope="module")
def demo() -> httpx.Client:
    base_url = os.environ.get("BASE_URL")
    if not base_url:
        pytest.skip("route smoke test runs against the seeded container: set BASE_URL")
    client = httpx.Client(base_url=base_url, timeout=60, follow_redirects=True)
    login = client.get("/accounts/login/")
    token = re.search(r'name="csrfmiddlewaretoken"\s+value="([^"]+)"', login.text)
    assert token, "no CSRF token on the login page"
    resp = client.post(
        "/accounts/login/", data={**DEMO, "csrfmiddlewaretoken": token.group(1)}
    )
    assert "/accounts/login" not in str(resp.url), "demo login failed: run seed_market"
    yield client
    client.close()


def _named_routes() -> list[tuple[str, str]]:
    """(name, route) per named core route, e.g. ('property_detail', 'properties/<int:pk>/')."""
    return [
        (p.name, str(p.pattern))
        for p in urlpatterns
        if getattr(p, "name", None) and p.name not in SKIP_NAMES
    ]


def _path(demo: httpx.Client, route: str) -> str:
    """Fill the route's id from the first matching link on its section's list page."""
    if not PARAM.search(route):
        return "/" + route
    section = route.split("/")[0]
    listing = demo.get(f"/{section}/")
    found = re.search(rf'href="/{section}/(\d+)/', listing.text)
    if not found:
        pytest.skip(f"no {section} id on /{section}/ for the demo user")
    return "/" + PARAM.sub(found.group(1), route, count=1)


@pytest.mark.parametrize("name,route", sorted(set(_named_routes())))
def test_route_is_not_5xx(demo: httpx.Client, name: str, route: str) -> None:
    path = _path(demo, route)
    resp = demo.get(path)
    assert resp.status_code < 500, f"{name}: GET {path} -> {resp.status_code}"

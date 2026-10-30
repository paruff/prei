"""Steps for journey.feature: the investor journey over HTTP against BASE_URL."""

from __future__ import annotations

import os
import re

import httpx
import pytest
from pytest_bdd import given, parsers, then, when

DEMO_USERNAME = "demo"
DEMO_PASSWORD = "DemoPass123!"  # noqa: S105 - seed_data demo credential
CITY, STATE = "Dallas", "TX"


class JourneyCtx:
    def __init__(self) -> None:
        self.client: httpx.Client | None = None
        self.growth_area_id: str | None = None
        self.page: str = ""
        self.screener: str = ""


@pytest.fixture
def ctx() -> JourneyCtx:
    return JourneyCtx()


def _csrf(client: httpx.Client, path: str) -> str:
    resp = client.get(path)
    assert resp.status_code == 200, f"GET {path} -> {resp.status_code}"
    match = re.search(r'name="csrfmiddlewaretoken"\s+value="([^"]+)"', resp.text)
    assert match, f"no CSRF token on {path}"
    return match.group(1)


def _text(html: str) -> str:
    html = re.sub(r"<(script|style).*?</\1>", "", html, flags=re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


def _metric(html: str, name: str) -> str:
    match = re.search(rf'data-metric="{name}">([^<]+)<', html)
    assert match, f"metric {name!r} not on page: {_text(html)[:300]}"
    return match.group(1).strip()


@given("I am signed in as the demo investor")
def signed_in(ctx: JourneyCtx) -> None:
    base_url = os.environ.get("BASE_URL")
    if not base_url:
        pytest.skip("journey runs against the seeded container: set BASE_URL")
    ctx.client = httpx.Client(base_url=base_url, timeout=60, follow_redirects=True)
    resp = ctx.client.post(
        "/accounts/login/",
        data={
            "username": DEMO_USERNAME,
            "password": DEMO_PASSWORD,
            "csrfmiddlewaretoken": _csrf(ctx.client, "/accounts/login/"),
        },
    )
    assert resp.status_code == 200
    assert "/accounts/login" not in str(resp.url), "demo login failed: run seed_market"


@when("I open the growth areas list")
def open_growth_areas(ctx: JourneyCtx) -> None:
    resp = ctx.client.get("/growth/")
    assert resp.status_code == 200
    ctx.page = resp.text


@then("Dallas, TX is ranked with a composite score")
def dallas_ranked(ctx: JourneyCtx) -> None:
    text = _text(ctx.page)
    assert re.search(rf"\b{CITY}\s+{STATE}\b.*?\d+\.\d{{2}}", text), text[:500]
    discover = re.search(r'href="[^"]*discovery/\?growth_area_id=(\d+)"', ctx.page)
    ids = re.findall(r"growth_area_id=(\d+)", ctx.page)
    assert discover or ids, "no discovery link for the ranked area"
    ctx.growth_area_id = discover.group(1) if discover else ids[0]


@when("I discover VRM properties in Dallas, TX")
def discover_vrm(ctx: JourneyCtx) -> None:
    path = f"/discovery/?growth_area_id={ctx.growth_area_id}"
    resp = ctx.client.post(
        path,
        data={
            "growth_area_id": ctx.growth_area_id,
            "sources": ["vrm"],
            "csrfmiddlewaretoken": _csrf(ctx.client, path),
        },
    )
    assert resp.status_code == 200, resp.status_code


@then(parsers.parse('the screener lists "{first}" and "{second}"'))
def screener_lists(ctx: JourneyCtx, first: str, second: str) -> None:
    resp = ctx.client.get(f"/pipeline/screener/?growth_area_id={ctx.growth_area_id}")
    assert resp.status_code == 200
    ctx.screener = resp.text
    for address in (first, second):
        assert address in resp.text, f"{address} missing from screener"


@when(parsers.parse('I open "{address}" from the screener'))
def open_from_screener(ctx: JourneyCtx, address: str) -> None:
    row = re.search(
        rf'href="(/pipeline/\d+/)"\s*>\s*{re.escape(address)}', ctx.screener
    )
    assert row, f"no detail link for {address} in the screener"
    resp = ctx.client.get(row.group(1))
    assert resp.status_code == 200
    ctx.page = resp.text


@then(
    parsers.parse('its gross yield is "{yield_pct}" and its price-to-rent is "{ptr}"')
)
def yield_and_ptr(ctx: JourneyCtx, yield_pct: str, ptr: str) -> None:
    assert _metric(ctx.page, "gross-yield") == yield_pct
    assert _metric(ctx.page, "price-to-rent") == ptr


@then("it shows NOI, cap rate, cash-on-cash and DSCR")
def shows_kpis(ctx: JourneyCtx) -> None:
    for name in ("noi", "cap-rate", "cash-on-cash", "dscr"):
        assert _metric(ctx.page, name)

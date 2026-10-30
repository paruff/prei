"""Steps for journey.feature: the investor journey over HTTP against BASE_URL."""

from __future__ import annotations

import os
import re
from html.parser import HTMLParser

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
        self.detail_path: str = ""


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
    ctx.detail_path = row.group(1)
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


# ── Steps 5-7: offer, due diligence, closing, own ────────────────────────────


def _post(ctx: JourneyCtx, path: str, data: dict):
    """POST with the session's CSRF token (the cookie set at login)."""
    token = ctx.client.cookies.get("csrftoken")
    assert token, "no csrftoken cookie: sign in first"
    return ctx.client.post(path, data={**data, "csrfmiddlewaretoken": token})


def _stage(html: str) -> str:
    match = re.search(r'badge-stage">([^<]+)<', html)
    assert match, "no stage badge on the detail page"
    return match.group(1).strip().upper().replace(" ", "_")


def _advance_to(ctx: JourneyCtx, stage: str) -> None:
    for _ in range(8):
        page = ctx.client.get(ctx.detail_path).text
        if _stage(page) == stage:
            ctx.page = page
            return
        resp = _post(
            ctx,
            f"{ctx.detail_path}advance-stage/",
            {"action": "advance", "next": ctx.detail_path},
        )
        assert resp.status_code == 200, resp.status_code
    pytest.fail(f"never reached {stage}; at {_stage(page)}")


@when("I discover VRM properties in the seeded market")
def discover_seeded_market(ctx: JourneyCtx) -> None:
    dallas_ranked(ctx)
    discover_vrm(ctx)
    screener_lists(ctx, "1200 Seed Pass Ln", "3400 Seed Fail Ct")


@when("I advance it to the Offer stage")
def advance_to_offer(ctx: JourneyCtx) -> None:
    _advance_to(ctx, "OFFER")


@when("I advance it to the Due Diligence stage")
def advance_to_dd(ctx: JourneyCtx) -> None:
    _advance_to(ctx, "DUE_DILIGENCE")


@when("I advance it to the Closing stage")
def advance_to_closing(ctx: JourneyCtx) -> None:
    _advance_to(ctx, "CLOSING")


@when(parsers.parse("I record an offer of {price:d}"))
def record_offer(ctx: JourneyCtx, price: int) -> None:
    resp = _post(ctx, f"{ctx.detail_path}offer/", {"offer_price": str(price)})
    assert resp.status_code == 200
    ctx.page = resp.text


@then("the offer is listed for the property")
def offer_listed(ctx: JourneyCtx) -> None:
    assert "175,000.00" in ctx.page, _text(ctx.page)[:500]


@when("I mark due diligence go")
def dd_go(ctx: JourneyCtx) -> None:
    resp = _post(
        ctx,
        f"{ctx.detail_path}dd/",
        {
            "inspection_completed": "on",
            "title_clear": "on",
            "insurance_quoted": "on",
            "go_no_go": "go",
        },
    )
    assert resp.status_code == 200
    assert "Due diligence checklist saved" in resp.text


@when(parsers.parse("I close the deal at {price:d}"))
def close_deal(ctx: JourneyCtx, price: int) -> None:
    resp = _post(
        ctx,
        f"{ctx.detail_path}closing/",
        {
            "final_purchase_price": str(price),
            "closing_date": "2026-10-01",
            "closing_costs": "3500",
            "loan_amount": "131250",
            "down_payment": "43750",
            "lender": "Seed Bank",
        },
    )
    assert resp.status_code == 200
    ctx.page = resp.text
    assert "/portfolio" in str(resp.url), f"closing ended at {resp.url}"


def _portfolio_row(html: str) -> str:
    rows = re.findall(r"<tr[^>]*>.*?</tr>", html, flags=re.S)
    mine = [r for r in rows if "1200 Seed Pass Ln" in r]
    assert mine, f"1200 Seed Pass Ln not in the portfolio: {_text(html)[:500]}"
    return mine[0]


@then("it is in the portfolio")
def in_portfolio(ctx: JourneyCtx) -> None:
    resp = ctx.client.get("/portfolio/")
    assert resp.status_code == 200
    ctx.page = resp.text
    assert "No data" in _portfolio_row(ctx.page), "fresh acquisition has no actuals"


class _FormParser(HTMLParser):
    """Collect the action and default field values of the form posting to `action`."""

    def __init__(self, action: str) -> None:
        super().__init__()
        self.target, self.action, self.fields, self.options = action, None, {}, {}
        self._in, self._select = False, None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "form" and a.get("action") == self.target:
            self._in, self.action = True, a["action"]
        elif self._in and tag == "select":
            self._select = a["name"]
            self.options[self._select] = []
        elif self._in and tag == "option" and self._select:
            self.options[self._select].append(a.get("value", ""))
        elif self._in and tag == "input" and a.get("name"):
            self.fields[a["name"]] = a.get("value", "")

    def handle_endtag(self, tag):
        if tag == "form":
            self._in = False
        elif tag == "select":
            self._select = None


@when("I enter monthly actuals for it")
def enter_actuals(ctx: JourneyCtx) -> None:
    """Fill in and submit the actuals form on the portfolio dashboard."""
    prop_id = re.search(r'data-property-id="(\d+)"', _portfolio_row(ctx.page))
    assert prop_id, "no property id in the portfolio row"
    form = _FormParser("/portfolio/actuals/add/")
    form.feed(ctx.page)
    assert form.action, "no actuals form on the portfolio dashboard"
    assert prop_id.group(1) in form.options["property_id"], "property not in the form"
    entered = {
        "property_id": prop_id.group(1),  # chosen from the form's select
        "month": "2026-10",  # what <input type="month"> submits
        "actual_rent_collected": "1800.00",
        "actual_vacancy_days": "0",
        "actual_expenses": "400.00",
        "actual_maintenance": "100.00",
    }
    missing = set(entered) - {"property_id"} - set(form.fields)
    assert not missing, f"form has no input for {missing}"
    resp = _post(ctx, form.action, {**form.fields, **entered})
    assert resp.status_code == 200
    ctx.page = resp.text


@then("the portfolio shows its actuals")
def shows_actuals(ctx: JourneyCtx) -> None:
    assert _metric(_portfolio_row(ctx.page), "latest-actuals") == "$1,800 (Oct 2026)"

"""Steps for journey.feature: the investor journey over HTTP against BASE_URL."""

from __future__ import annotations

import os
import re
from decimal import Decimal
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

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
        self.url: str = ""
        self.discovery_href: str = ""
        self.screener_url: str = ""
        self.screener: str = ""
        self.detail_path: str = ""
        self.offer: int = 0
        self.leasing_path: str = ""
        self.lease: tuple[str, int] = ("", 0)


@pytest.fixture
def ctx() -> JourneyCtx:
    return JourneyCtx()


def _csrf(client: httpx.Client, path: str) -> str:
    resp = client.get(path)
    assert resp.status_code == 200, f"GET {path} -> {resp.status_code}"
    match = re.search(r'name="csrfmiddlewaretoken"\s+value="([^"]+)"', resp.text)
    assert match, f"no CSRF token on {path}"
    return match.group(1)


def _visit(ctx: JourneyCtx, resp: httpx.Response) -> httpx.Response:
    """Record the page the browser is now on (after redirects)."""
    ctx.page, ctx.url = resp.text, str(resp.url)
    return resp


def _links(html: str) -> list[tuple[str, str]]:
    """(href, visible text) of every anchor on the page."""
    return [
        (href, _text(inner))
        for href, inner in re.findall(
            r'<a\s[^>]*?href="([^"#][^"]*)"[^>]*>(.*?)</a>', html, flags=re.S
        )
    ]


def _click(ctx: JourneyCtx, label: str, href: str | None = None) -> httpx.Response:
    """Follow the link on the current page whose text matches `label` (regex).

    The journey may only move by clicking: a missing link fails the scenario.
    """
    hits = [
        h
        for h, t in _links(ctx.page)
        if re.search(label, t) and (href is None or re.search(href, h))
    ]
    assert hits, (
        f"no link {label!r} on {ctx.url}; links: "
        f"{[t for _, t in _links(ctx.page)][:25]}"
    )
    resp = ctx.client.get(urljoin(ctx.url, unescape(hits[0])))
    assert resp.status_code == 200, f"{hits[0]} -> {resp.status_code}"
    return _visit(ctx, resp)


def _submit(ctx: JourneyCtx, action: str, data: dict | None = None) -> httpx.Response:
    """Submit the form on the current page whose action matches `action` (regex).

    Starts from the form's own fields (CSRF token, hidden inputs, defaults), so
    a form that is not on the page cannot be posted to.
    """
    form = _FormParser(action, ctx.url)
    form.feed(ctx.page)
    assert form.action is not None, (
        f"no form posting to {action!r} on {ctx.url}; "
        f"forms: {re.findall(r'<form[^>]*>', ctx.page)}"
    )
    fields = {**form.fields, **(data or {})}
    fields = {k: v for k, v in fields.items() if v is not None}  # None: leave blank
    resp = ctx.client.post(urljoin(ctx.url, form.action), data=fields)
    assert resp.status_code == 200, f"{form.action} -> {resp.status_code}"
    return _visit(ctx, resp)


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
    _visit(ctx, resp)
    assert "/accounts/login" not in str(resp.url), "demo login failed: run seed_market"


@when("I open the growth areas list")
def open_growth_areas(ctx: JourneyCtx) -> None:
    _click(ctx, r"Growth Areas")


@then("Dallas, TX is ranked with a composite score")
def dallas_ranked(ctx: JourneyCtx) -> None:
    rows = re.findall(r"<tr[^>]*>.*?</tr>", ctx.page, flags=re.S)
    dallas = [r for r in rows if f"<td>{CITY}</td>" in r and f"<td>{STATE}</td>" in r]
    assert dallas, f"no {CITY}, {STATE} row: {_text(ctx.page)[:500]}"
    score = re.search(r'score-num[^"]*">\s*([\d.]+)\s*<', dallas[0])
    assert score, f"no composite score in the Dallas row: {_text(dallas[0])}"
    assert 0 <= Decimal(score.group(1)) <= 100, score.group(1)
    link = re.search(r'href="([^"]*discovery/\?growth_area_id=(\d+))"', dallas[0])
    assert link, "no discovery link in the Dallas row"
    ctx.discovery_href, ctx.growth_area_id = unescape(link.group(1)), link.group(2)


@when("I discover VRM properties in Dallas, TX")
def discover_vrm(ctx: JourneyCtx) -> None:
    # the Dallas row's own link, then the form it opens
    resp = ctx.client.get(urljoin(ctx.url, ctx.discovery_href))
    assert resp.status_code == 200, resp.status_code
    _visit(ctx, resp)
    _submit(ctx, r"growth_area_id", {"sources": ["vrm"]})


@then(parsers.parse('the screener lists "{first}" and "{second}"'))
def screener_lists(ctx: JourneyCtx, first: str, second: str) -> None:
    _click(ctx, r"\bScreen\b")  # Purchase Pipeline menu
    ctx.screener, ctx.screener_url = ctx.page, ctx.url
    for address in (first, second):
        assert address in ctx.page, f"{address} missing from screener"


def _screener_row(html: str, address: str) -> str:
    rows = re.findall(r"<tr[^>]*>.*?</tr>", html, flags=re.S)
    mine = [r for r in rows if address in r]
    assert mine, f"{address} missing from screener"
    return _text(mine[0])


@then(parsers.parse('"{address}" is screened {verdict}'))
def screened_verdict(ctx: JourneyCtx, address: str, verdict: str) -> None:
    chip = {"Passed": "✓ Passed", "Failed": "✗ Failed"}[verdict]
    row = _screener_row(ctx.screener, address)
    assert chip in row, f"{address} is not {chip}: {row}"


@when(parsers.parse('I open "{address}" from the screener'))
def open_from_screener(ctx: JourneyCtx, address: str) -> None:
    if ctx.url != ctx.screener_url:
        _click(ctx, r"\bScreen\b")
    _click(ctx, rf"^{re.escape(address)}$", r"^/pipeline/\d+/$")
    ctx.detail_path = urlparse(ctx.url).path


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


def _stage(html: str) -> str:
    match = re.search(r'badge-stage">([^<]+)<', html)
    assert match, "no stage badge on the detail page"
    return match.group(1).strip().upper().replace(" ", "_")


def _on_detail(ctx: JourneyCtx) -> None:
    """Be on the property page, going back by a link if the walk left it."""
    if urlparse(ctx.url).path != ctx.detail_path:
        _click(ctx, r".", rf"^{ctx.detail_path}$")


def _advance_to(ctx: JourneyCtx, stage: str) -> None:
    _on_detail(ctx)
    for _ in range(8):
        if _stage(ctx.page) == stage:
            return
        _submit(ctx, r"/advance-stage/$", {"action": "advance"})
    pytest.fail(f"never reached {stage}; at {_stage(ctx.page)}")


@when("I discover VRM properties in the seeded market")
def discover_seeded_market(ctx: JourneyCtx) -> None:
    open_growth_areas(ctx)
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
    _on_detail(ctx)
    _click(ctx, r"Add Offer")
    # the form's date is blank (its `'now'|date` default renders empty), so the
    # investor types one
    _submit(ctx, r"/offer/$", {"offer_price": str(price), "offer_date": "2026-10-01"})
    ctx.offer = price


@then("the offer is listed for the property")
def offer_listed(ctx: JourneyCtx) -> None:
    assert f"${ctx.offer:,}" in ctx.page, _text(ctx.page)[:500]


@when("I mark due diligence go")
def dd_go(ctx: JourneyCtx) -> None:
    _on_detail(ctx)
    _click(ctx, r"Due Diligence")
    _submit(
        ctx,
        r"/dd/$",
        {
            "inspection_completed": "on",
            "title_clear": "on",
            "insurance_quoted": "on",
            "go_no_go": "go",
        },
    )
    assert "Due diligence checklist saved" in ctx.page


@when(parsers.parse("I close the deal at {price:d}"))
def close_deal(ctx: JourneyCtx, price: int) -> None:
    loan = price * 3 // 4  # 75% LTV: loan + down payment = price
    _on_detail(ctx)
    _click(ctx, r"Close Deal")
    _submit(
        ctx,
        r"/closing/$",
        {
            "final_purchase_price": str(price),
            "closing_date": "2026-10-01",
            "closing_costs": "3500",
            "loan_amount": str(loan),
            "down_payment": str(price - loan),
            "lender": "Seed Bank",
        },
    )
    assert "/portfolio" in ctx.url, f"closing ended at {ctx.url}"


def _portfolio_row(html: str) -> str:
    rows = re.findall(r"<tr[^>]*>.*?</tr>", html, flags=re.S)
    mine = [r for r in rows if "1200 Seed Pass Ln" in r]
    assert mine, f"1200 Seed Pass Ln not in the portfolio: {_text(html)[:500]}"
    return mine[0]


@then("it is in the portfolio")
def in_portfolio(ctx: JourneyCtx) -> None:
    _click(ctx, r"^Portfolio$")
    assert "No data" in _portfolio_row(ctx.page), "fresh acquisition has no actuals"


class _FormParser(HTMLParser):
    """Collect the action and default field values of the first form whose action
    matches the regex `target` (a form without an action posts to `page_url`)."""

    def __init__(self, target: str, page_url: str = "") -> None:
        super().__init__()
        self.target, self.page_url = target, page_url
        self.action, self.fields, self.options = None, {}, {}
        self._in, self._done, self._select = False, False, None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "form" and not self._done:
            action = unescape(a.get("action") or self.page_url)
            if re.search(self.target, action):
                self._in, self.action = True, action
        elif self._in and tag == "select" and a.get("name"):
            self._select = a["name"]
            self.options[self._select] = []
        elif self._in and tag == "option" and self._select:
            self.options[self._select].append(a.get("value", ""))
        elif self._in and tag == "input" and a.get("name"):
            if a.get("type") not in ("checkbox", "radio") or "checked" in a:
                self.fields[a["name"]] = a.get("value", "")

    def handle_endtag(self, tag):
        if tag == "form" and self._in:
            self._in, self._done = False, True
        elif tag == "select":
            self._select = None


@when("I enter monthly actuals for it")
def enter_actuals(ctx: JourneyCtx) -> None:
    """Fill in and submit the actuals form on the portfolio dashboard."""
    _click(ctx, r"^Portfolio$")
    prop_id = re.search(r'data-property-id="(\d+)"', _portfolio_row(ctx.page))
    assert prop_id, "no property id in the portfolio row"
    form = _FormParser(r"/portfolio/actuals/add/$", ctx.url)
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
    _submit(ctx, r"/portfolio/actuals/add/$", entered)


@then("the portfolio shows its actuals")
def shows_actuals(ctx: JourneyCtx) -> None:
    assert _metric(_portfolio_row(ctx.page), "latest-actuals") == "$1,800 (Oct 2026)"


# ── Steps 8-9: BRRRR and leasing on the acquired property ────────────────────


@when(parsers.parse("I run the BRRRR calculator with rehab {rehab:d} and ARV {arv:d}"))
def run_brrrr(ctx: JourneyCtx, rehab: int, arv: int) -> None:
    # the acquired property's price and rent, as the portfolio shows them
    # columns: Address, Price, Down Payment, Est. Rent, ...
    cells = _cells(_portfolio_row(ctx.page))
    price, rent = _dollars(cells[1]), _dollars(cells[3])
    assert price == ctx.offer and rent > 0, f"portfolio row {cells[:4]}"
    _click(ctx, r"BRRRR")
    # the page computes in JavaScript and has no form; its view also takes a POST
    token = ctx.client.cookies.get("csrftoken")
    assert token, "no csrftoken cookie: sign in first"
    resp = ctx.client.post(
        ctx.url,
        data={
            "purchase_price": str(price),
            "rehab_cost": str(rehab),
            "arv": str(arv),
            "monthly_rent_post_rehab": str(rent),
            "annual_operating_expenses": "4200",
            "csrfmiddlewaretoken": token,
        },
    )
    assert resp.status_code == 200, resp.status_code
    _visit(ctx, resp)


@then(parsers.parse('the BRRRR verdict is "{verdict}"'))
def brrrr_verdict(ctx: JourneyCtx, verdict: str) -> None:
    assert _metric(ctx.page, "brrrr-verdict") == verdict
    assert Decimal(_metric(ctx.page, "brrrr-cash-left")) < 0


@when("I add it to the leasing pipeline")
def add_to_leasing(ctx: JourneyCtx) -> None:
    _click(ctx, r"^Portfolio$")
    prop_id = re.search(r'data-property-id="(\d+)"', _portfolio_row(ctx.page))
    assert prop_id, "acquired property not in the portfolio"
    _click(ctx, r"Leasing")
    _click(ctx, r"Add", r"/leasing/add/$")
    _submit(
        ctx,
        r"/leasing/add/$",
        {"property_record": prop_id.group(1), "asking_rent": "1800"},
    )
    _click(ctx, r"View Details", r"^/leasing/\d+/$")
    ctx.leasing_path = urlparse(ctx.url).path


@when(parsers.parse('I lease it to "{tenant}" at {rent:d} a month'))
def lease_it(ctx: JourneyCtx, tenant: str, rent: int) -> None:
    ctx.lease = (tenant, rent)
    steps = [
        ("Record Showing", "showing/", {}),
        (
            "Record Application",
            "application/",
            {"applicant_name": tenant, "application_date": "2026-10-05"},
        ),
        ("Screen Applicant", "screening/", {"screening_passed": "true"}),
        (
            "Record Lease",
            "lease/",
            {
                "lease_start_date": "2026-11-01",
                "lease_end_date": "2027-10-31",
                "monthly_rent": str(rent),
            },
        ),
        ("Move In", "move-in/", {"move_in_date": "2026-11-01"}),
        ("Stabilize", "stabilize/", {"stabilized_date": "2026-12-01"}),
    ]
    for label, suffix, data in steps:
        _click(ctx, label, rf"^{ctx.leasing_path}{suffix}$")
        # untick "advance": each stage is recorded in turn, none skipped
        _submit(ctx, rf"{ctx.leasing_path}{suffix}$", {**data, "advance": None})


@then("it is stabilized in leasing")
def leasing_stabilized(ctx: JourneyCtx) -> None:
    assert _stage(ctx.page) == "STABILIZED"
    assert "Filled" in ctx.page
    text = _text(ctx.page)
    tenant, rent = ctx.lease
    assert f"Name {tenant}" in text, text[:500]
    assert f"Monthly Rent ${rent:,}" in text, text[:500]


# ── G4.1: the figures an investor acts on (AC-16) ────────────────────────────


def _dollars(text: str) -> Decimal:
    match = re.search(r"-?\$?\s*-?[\d,]+(?:\.\d+)?", text)
    assert match, f"no amount in {text!r}"
    return Decimal(re.sub(r"[^\d.\-]", "", match.group(0)))


def _cells(row: str) -> list[str]:
    return [_text(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", row, flags=re.S)]


@then(parsers.parse("the portfolio shows its purchase price of {price:d}"))
def shows_purchase_price(ctx: JourneyCtx, price: int) -> None:
    # columns: Address, Price, Down Payment, Est. Rent, Monthly CF, ...
    shown = _dollars(_cells(_portfolio_row(ctx.page))[1])
    assert shown == price, f"portfolio price {shown} is not the closing price {price}"


@then("the portfolio equity is value minus loan, not the price")
def equity_is_value_minus_loan(ctx: JourneyCtx) -> None:
    # closed at 95,000 with a 71,250 loan (75% LTV): equity can never be the price
    kpi = re.search(r"Total Equity</div>\s*<div[^>]*>([^<]+)<", ctx.page)
    assert kpi, "no Total Equity tile on the portfolio"
    equity = _dollars(kpi.group(1))
    assert equity < 95000, f"equity {equity} is the price, not value minus loan"


@then(parsers.parse("the portfolio cash flow is below the gross rent of {rent:d}"))
def cash_flow_is_net(ctx: JourneyCtx, rent: int) -> None:
    cash_flow = _dollars(_cells(_portfolio_row(ctx.page))[4])
    assert cash_flow < rent, f"cash flow {cash_flow} is gross rent, not net of costs"


@then("the dashboard verdict agrees with its cash-on-cash")
def dashboard_verdict_agrees(ctx: JourneyCtx) -> None:
    html = _click(ctx, r"PREI").text
    rows = [
        r
        for r in re.findall(r"<tr[^>]*>.*?</tr>", html, flags=re.S)
        if "1200 Seed Pass Ln" in r
    ]
    assert rows, "acquired property not on the dashboard"
    coc = _dollars(_cells(rows[0])[1])
    verdict = re.search(r'data-verdict="(\w*)"', rows[0]).group(1)
    assert not (coc < 8 and verdict == "A"), f"CoC {coc}% is rated Strong Buy"


@then(parsers.parse("the portfolio shows its down payment share of {share}"))
def shows_down_payment_share(ctx: JourneyCtx, share: str) -> None:
    # closing loan + down payment = price, so the share is down payment / price
    shown = _cells(_portfolio_row(ctx.page))[2]
    assert shown == share, f"portfolio down payment {shown!r} is not {share!r}"

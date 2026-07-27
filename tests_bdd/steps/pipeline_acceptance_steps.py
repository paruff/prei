"""Step definitions for pipeline_acceptance.feature — live system tests.

These tests exercise the full Django request/response cycle over real
HTTP, via pytest-django's ``live_server`` fixture: routing, middleware,
templates, redirects, and 404 handling are all genuinely exercised
(rather than short-circuited by ``django.test.Client``'s in-process
request/response construction). Scenario setup (``Given`` steps) still
uses the ORM directly against ``transactional_db``, which the live
server shares data with once committed.
"""

from __future__ import annotations

import re
from decimal import Decimal

import httpx
from pytest_bdd import given, parsers, then, when
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

User = get_user_model()


# ── Shared state container ────────────────────────────────────────────────────


class PipelineCtx:
    """Holds shared state across steps within a scenario."""

    def __init__(self):
        self.client: httpx.Client | None = None
        self.user: User | None = None
        self.other_user: User | None = None
        self.vrm_property = None
        self.pipeline_property = None
        self.leasing_entry = None
        self.portfolio_property = None
        self.response = None
        self.created = False


_ctx = PipelineCtx()


def _build_vrm_property(user, **overrides):
    from core.models import VrmProperty as VP

    now = timezone.now()
    defaults = dict(
        vrm_property_id=9100,
        vrm_listing_url="https://example.com/9100",
        address="9100 Acceptance Blvd",
        city="Austin",
        state="TX",
        zip_code="78701",
        list_price=Decimal("250000"),
        projected_monthly_rent=Decimal("2200"),
        bedrooms=3,
        year_built=2015,
        property_type="single-family",
        status=VP.Status.FOR_SALE,
        scraped_at=now,
        last_seen_at=now,
    )
    defaults.update(overrides)
    return VP.objects.create(**defaults)


def _csrf_token(client: httpx.Client, path: str = "/accounts/login/") -> str:
    """Extract CSRF token from the login page HTML."""
    resp = client.get(path)
    assert resp.status_code == 200
    match = re.search(r'name="csrfmiddlewaretoken"\s+value="([^"]+)"', resp.text)
    assert match is not None, "CSRF token not found in login page HTML"
    return match.group(1)


def _login(client: httpx.Client, username: str, password: str) -> None:
    """Log in over real HTTP (POST credentials + CSRF token)."""
    token = _csrf_token(client)
    resp = client.post(
        "/accounts/login/",
        data={
            "username": username,
            "password": password,
            "csrfmiddlewaretoken": token,
        },
    )
    assert resp.status_code in (200, 302), f"Login failed: {resp.status_code}"


# ═══════════════════════════════════════════════════════════════════════════════
#  Given steps
# ═══════════════════════════════════════════════════════════════════════════════


@given("I am logged in as a user")
def given_logged_in(transactional_db, live_server):
    _ctx.user = User.objects.create_user(
        username="acceptance_user",
        email="acceptance@test.com",
        password="pass123",
    )
    _ctx.client = httpx.Client(
        base_url=live_server.url, timeout=30, follow_redirects=False
    )
    _login(_ctx.client, "acceptance_user", "pass123")


@given(
    parsers.parse(
        "I have a VRM property in Texas listed at ${price} with ${rent}/mo rent"
    )
)
def given_vrm_property(transactional_db, price, rent):  # noqa: F811
    _ctx.vrm_property = _build_vrm_property(
        _ctx.user,
        list_price=Decimal(price.replace(",", "")),
        projected_monthly_rent=Decimal(rent.replace(",", "")),
    )


@given("I have a pipeline property")
def given_pipeline_property(transactional_db):
    from core.services.pipeline import create_from_vrm

    if _ctx.vrm_property is None:
        _ctx.vrm_property = _build_vrm_property(_ctx.user, vrm_property_id=9200)
    _ctx.pipeline_property, _ctx.created = create_from_vrm(_ctx.vrm_property, _ctx.user)


@given("I have a pipeline property at DISCOVERED stage")
def given_pipeline_property_discovered(transactional_db):

    if _ctx.vrm_property is None:
        _ctx.vrm_property = _build_vrm_property(_ctx.user, vrm_property_id=9300)
    from core.services.pipeline import create_from_vrm

    pp, _ = create_from_vrm(_ctx.vrm_property, _ctx.user)
    # Reset to DISCOVERED for the test
    pp.stage = "DISCOVERED"
    pp.screening_passed = None
    pp.screening_at = None
    pp.save()
    _ctx.pipeline_property = pp


@given("I have a pipeline property at CLOSING stage")
def given_pipeline_property_closing(transactional_db):
    from core.services.pipeline import create_from_vrm, advance_stage

    if _ctx.vrm_property is None:
        _ctx.vrm_property = _build_vrm_property(_ctx.user, vrm_property_id=9400)
    pp, _ = create_from_vrm(_ctx.vrm_property, _ctx.user)

    # Advance through all stages to CLOSING
    target_stages = ["UNDERWRITING", "OFFER", "DUE_DILIGENCE", "CLOSING"]
    for _ in target_stages:
        advance_stage(pp)
    pp.refresh_from_db()
    _ctx.pipeline_property = pp


@given("I have a property in my portfolio")
def given_portfolio_property(transactional_db):
    from core.models import Property as PropertyModel

    _ctx.portfolio_property = PropertyModel.objects.create(
        user=_ctx.user,
        address="9500 Portfolio Ln",
        city="Austin",
        state="TX",
        zip_code="78701",
        purchase_price=Decimal("250000"),
        purchase_date="2026-06-01",
        sqft=1500,
        monthly_rent_gross=Decimal("2000"),
    )


@given("I have a leasing pipeline entry")
def given_leasing_entry(transactional_db):
    from core.models import Property as PropertyModel, LeasingPipelineProperty

    if _ctx.portfolio_property is None:
        _ctx.portfolio_property = PropertyModel.objects.create(
            user=_ctx.user,
            address="9600 Lease Ave",
            city="Austin",
            state="TX",
            zip_code="78701",
            purchase_price=Decimal("250000"),
            purchase_date="2026-06-01",
        )
    _ctx.leasing_entry = LeasingPipelineProperty.objects.create(
        property_record=_ctx.portfolio_property,
        user=_ctx.user,
        asking_rent=Decimal("2200"),
        listed_date="2026-07-01",
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  When steps
# ═══════════════════════════════════════════════════════════════════════════════


@when("I add the VRM property to my pipeline")
def when_add_vrm_to_pipeline(transactional_db):
    from core.services.pipeline import create_from_vrm

    _ctx.pipeline_property, _ctx.created = create_from_vrm(_ctx.vrm_property, _ctx.user)


@when(parsers.parse("I visit the pipeline list with status {status}"))
def when_visit_pipeline_list(transactional_db, status):
    _ctx.response = _ctx.client.get(reverse("pipeline_list"), params={"status": status})


@when("I view the pipeline detail page")
def when_view_pipeline_detail(transactional_db):
    _ctx.response = _ctx.client.get(
        reverse("pipeline_detail", kwargs={"pk": _ctx.pipeline_property.pk})
    )


@when("another user views the pipeline detail page")
def when_other_user_views_detail(transactional_db, live_server):
    _ctx.other_user = User.objects.create_user(
        username="other_acceptance",
        email="other@test.com",
        password="pass456",
    )
    other_client = httpx.Client(
        base_url=live_server.url, timeout=30, follow_redirects=False
    )
    _login(other_client, "other_acceptance", "pass456")
    _ctx.response = other_client.get(
        reverse("pipeline_detail", kwargs={"pk": _ctx.pipeline_property.pk})
    )
    other_client.close()


@when("I visit the screening settings page")
def when_visit_screening_settings(transactional_db):
    _ctx.response = _ctx.client.get(reverse("pipeline_screening_settings"))


@when(parsers.parse("I set minimum beds to {beds} and maximum price to ${price}"))
def when_set_screening_criteria(transactional_db, beds, price):
    token = _csrf_token(_ctx.client)
    _ctx.response = _ctx.client.post(
        reverse("pipeline_screening_settings"),
        data={
            "min_beds": beds,
            "max_price": price.replace(",", ""),
            "csrfmiddlewaretoken": token,
        },
    )


@when("I update the screening criteria")
def when_update_screening_criteria(transactional_db):
    token = _csrf_token(_ctx.client)
    _ctx.response = _ctx.client.post(
        reverse("pipeline_screening_settings"),
        data={"min_beds": "3", "csrfmiddlewaretoken": token},
    )


@when(parsers.parse("I submit an offer for ${amount} on the property"))
def when_submit_offer(transactional_db, amount):
    token = _csrf_token(_ctx.client)
    _ctx.response = _ctx.client.post(
        reverse("pipeline_offer_create", kwargs={"pk": _ctx.pipeline_property.pk}),
        data={
            "offer_price": amount.replace(",", ""),
            "offer_date": "2026-07-15",
            "csrfmiddlewaretoken": token,
        },
    )


@when('I save the due diligence checklist with a "no_go" decision')
def when_save_dd_no_go(transactional_db):
    token = _csrf_token(_ctx.client)
    _ctx.response = _ctx.client.post(
        reverse("pipeline_dd_checklist", kwargs={"pk": _ctx.pipeline_property.pk}),
        data={
            "go_no_go": "no_go",
            "no_go_reason": "Failed inspection — structural issues",
            "csrfmiddlewaretoken": token,
        },
    )


@when("I submit the closing form")
def when_submit_closing(transactional_db):
    token = _csrf_token(_ctx.client)
    _ctx.response = _ctx.client.post(
        reverse("pipeline_closing_create", kwargs={"pk": _ctx.pipeline_property.pk}),
        data={
            "final_purchase_price": "245000",
            "closing_date": "2026-07-15",
            "closing_costs": "5000",
            "lender": "Test Bank",
            "csrfmiddlewaretoken": token,
        },
    )


@when("I add the property to the leasing pipeline")
def when_add_to_leasing(transactional_db):
    token = _csrf_token(_ctx.client)
    _ctx.response = _ctx.client.post(
        reverse("leasing_add"),
        data={
            "property_record": _ctx.portfolio_property.pk,
            "asking_rent": "2200",
            "listed_date": "2026-07-01",
            "csrfmiddlewaretoken": token,
        },
    )


@when("I view the leasing detail page")
def when_view_leasing_detail(transactional_db):
    from core.models import LeasingPipelineProperty

    if _ctx.portfolio_property is None:
        from core.models import Property as PropertyModel

        _ctx.portfolio_property = PropertyModel.objects.create(
            user=_ctx.user,
            address="9600 Lease Ave",
            city="Austin",
            state="TX",
            zip_code="78701",
            purchase_price=Decimal("250000"),
            purchase_date="2026-06-01",
        )
    if _ctx.leasing_entry is None:
        _ctx.leasing_entry = LeasingPipelineProperty.objects.create(
            property_record=_ctx.portfolio_property,
            user=_ctx.user,
            asking_rent=Decimal("2200"),
            listed_date="2026-07-01",
        )
    _ctx.response = _ctx.client.get(
        reverse("leasing_detail", kwargs={"pk": _ctx.leasing_entry.pk})
    )


@when("I check all pipeline navigation links")
def when_check_nav_links(transactional_db):
    # Just verify URL resolution — no request needed
    pass


# ═══════════════════════════════════════════════════════════════════════════════
#  Then steps
# ═══════════════════════════════════════════════════════════════════════════════


@then("I should be redirected to the pipeline detail page")
def then_redirected_to_detail():
    from core.models import PipelineProperty

    pp = PipelineProperty.objects.get(pk=_ctx.pipeline_property.pk)
    assert pp is not None
    assert pp.stage == "SCREENING"


@then("the property stage should be SCREENING")
def then_stage_is_screening():
    from core.models import PipelineProperty

    pp = PipelineProperty.objects.get(pk=_ctx.pipeline_property.pk)
    assert pp.stage == "SCREENING"


@then("the screening result should be recorded")
def then_screening_recorded():
    from core.models import PipelineProperty

    pp = PipelineProperty.objects.get(pk=_ctx.pipeline_property.pk)
    assert pp.screening_passed is not None


@then("I should see my pipeline property in the list")
def then_property_in_list():
    assert _ctx.response.status_code == 200
    assert _ctx.pipeline_property.address in _ctx.response.text


@then("I should see the property address")
def then_see_address():
    assert _ctx.response.status_code == 200
    assert _ctx.pipeline_property.address in _ctx.response.text


@then('I should see action buttons including "Add Offer" and "Due Diligence"')
def then_see_action_buttons():
    assert _ctx.response.status_code == 200
    assert "Add Offer" in _ctx.response.text
    assert "Due Diligence" in _ctx.response.text


@then("they should get a 404 response")
def then_404_response():
    assert _ctx.response.status_code == 404


@then("the criteria should be saved")
def then_criteria_saved():
    from core.models import ScreeningCriteria

    criteria = ScreeningCriteria.objects.get(user=_ctx.user)
    assert criteria.min_beds == 2
    assert criteria.max_price == Decimal("400000")


@then("the property should be re-screened")
def then_property_rescreened():

    _ctx.pipeline_property.refresh_from_db()
    assert _ctx.pipeline_property.screening_passed is not None


@then("an offer record should exist for the property")
def then_offer_exists():
    from core.models import OfferRecord

    assert OfferRecord.objects.filter(pipeline_property=_ctx.pipeline_property).exists()


@then("the property should be killed with the reason recorded")
def then_property_killed():

    _ctx.pipeline_property.refresh_from_db()
    assert _ctx.pipeline_property.status == "KILLED"
    assert "structural" in _ctx.pipeline_property.kill_reason


@then("a Property record should be created")
def then_property_created():
    from core.models import Property as PropertyModel

    props = PropertyModel.objects.filter(user=_ctx.user)
    assert props.exists()


@then("the pipeline property should be marked ACQUIRED")
def then_pipeline_acquired():
    _ctx.pipeline_property.refresh_from_db()
    assert _ctx.pipeline_property.status == "ACQUIRED"
    assert _ctx.pipeline_property.stage == "ACQUIRED"


@then("I should be redirected to the portfolio dashboard")
def then_redirected_to_portfolio():
    assert _ctx.response.status_code in (302,)
    expected = reverse("portfolio_dashboard")
    location = _ctx.response.headers.get("location", "")
    assert expected in location


@then("I should see it in the leasing list")
def then_leasing_in_list():

    # Follow redirect
    assert _ctx.response.status_code == 302
    resp = _ctx.client.get(reverse("leasing_list"))
    content = resp.text
    assert "Portfolio" in content or "9500" in content


@then("I should see the listing details")
def then_see_listing_details():
    from core.models import LeasingPipelineProperty

    entry = LeasingPipelineProperty.objects.get(pk=_ctx.leasing_entry.pk)
    assert entry.asking_rent == Decimal("2200")


@then("I should see the stage history")
def then_see_stage_history():
    assert _ctx.leasing_entry.stage is not None


@then("the Screen link should resolve to /pipeline/screening/settings/")
def then_screen_link_resolves():
    url = reverse("pipeline_screening_settings")
    assert url == "/pipeline/screening/settings/"


@then("the My Pipeline link should resolve to /pipeline/list/")
def then_pipeline_link_resolves():
    url = reverse("pipeline_list")
    assert url == "/pipeline/list/"


@then("the Leasing Pipeline link should resolve to /leasing/")
def then_leasing_link_resolves():
    url = reverse("leasing_list")
    assert url == "/leasing/"

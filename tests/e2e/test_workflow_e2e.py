"""Full-workflow browser E2E: Growth Explorer → Discovery → Screening → Underwriting → Offer → Pipeline."""

import re

import pytest

pytestmark = pytest.mark.django_db(transaction=True)


class TestWorkflowJourney:
    def test_screener_requires_login(self, page) -> None:
        page.goto("/pipeline/screener/")
        assert "/accounts/login/" in page.url

    def test_full_workflow_journey(
        self, page, e2e_login, growth_area, discovery_sources
    ) -> None:
        # ── Growth Explorer renders ────────────────────────────────────
        page.goto("/growth-explorer/")
        assert page.locator("h1", has_text="Growth Area Explorer").is_visible()
        assert page.locator("#state-select").is_visible()

        # ── Discovery: seeded sources listed, run discovery ────────────
        page.goto(f"/discovery/?growth_area_id={growth_area.pk}")
        assert page.locator("#discover-btn").is_visible()
        assert page.locator("label", has_text="HUD REO").is_visible()
        assert page.locator("label", has_text="VRM (VA REO)").is_visible()

        page.click("#discover-btn")
        page.locator("#results-section:not([hidden])").wait_for(
            state="visible", timeout=30000
        )

        results_text = page.locator("#results-section").inner_text()
        assert "Discovered" in results_text
        # All four seeded sources pass screening (see Global Constraints note below).
        assert "Passed Screening" in results_text
        assert "100 Prime St" in page.inner_text("body")

        # ── Screener: property passed automatic screening ──────────────
        page.goto(f"/pipeline/screener/?growth_area_id={growth_area.pk}")
        row = page.locator("tr", has_text="100 Prime St")
        assert row.is_visible()
        assert row.locator(".chip-success", has_text="Passed").is_visible()

        # ── Advance to Underwriting via the screener action ────────────
        row.locator("button", has_text="Underwriting").click()
        assert page.locator(".message", has_text="moved to Underwriting").is_visible()

        # Extract the pipeline property pk from the address detail link.
        href = (
            page.locator("tr", has_text="100 Prime St")
            .locator('a[href*="/pipeline/"]')
            .first.get_attribute("href")
        )
        match = re.search(r"/pipeline/(\d+)/", href)
        assert match is not None
        pk = match.group(1)

        # ── Offer: record an offer on the property ─────────────────────
        page.goto(f"/pipeline/{pk}/offer/")
        page.fill('input[name="offer_price"]', "185000")
        page.fill('input[name="offer_date"]', "2026-08-20")
        page.click('button[type="submit"]:has-text("Submit Offer")')
        assert page.locator(".message", has_text="Offer recorded.").is_visible()

        # ── Pipeline list: card is present with UNDERWRITING badge ─────
        page.goto("/pipeline/list/")
        card = page.locator(".pipeline-card", has_text="100 Prime St")
        assert card.is_visible()
        assert card.locator(".badge-stage", has_text="Underwriting").is_visible()

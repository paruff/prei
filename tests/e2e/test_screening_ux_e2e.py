"""E2E tests for screening UX — filter bar, preview impact, version history."""

import pytest

pytestmark = pytest.mark.django_db(transaction=True)


class TestScreeningUX:
    def test_screener_page_renders(self, page, e2e_login) -> None:
        """Screening page loads with filter controls or empty state."""
        page.goto("/pipeline/screener/")
        # Page should render - either with filters (if properties exist) or empty state
        assert page.locator("h1", has_text="Screened Properties").is_visible()

    def test_preview_impact_button(self, page, e2e_login) -> None:
        """Preview Impact button exists on screening settings page."""
        page.goto("/pipeline/screening/settings/")
        btn = page.locator("button", has_text="Preview Impact")
        assert btn.is_visible()

    def test_version_history_displayed(self, page, e2e_login) -> None:
        """Screening settings page shows version history after save."""
        page.goto("/pipeline/screening/settings/")
        # Fill the hidden input field (synced with slider via JS)
        page.evaluate(
            """() => {
                var hidden = document.querySelector('[name="min_gross_yield_pct"]');
                if (hidden) hidden.value = '8';
            }"""
        )
        page.click('button[type="submit"]:has-text("Save")')
        page.wait_for_url("**/screening/settings/**")
        # Version history section should appear after first save
        assert page.locator("h2", has_text="Recent Versions").is_visible()

"""Smoke tests proving the Playwright harness binds to live_server and can log in."""

import pytest

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.flaky(reruns=0)]


class TestHarness:
    def test_page_loads_health_check(self, page) -> None:
        page.goto("/health/")
        assert page.locator("body").inner_text() != ""

    def test_health_returns_ok(self, page) -> None:
        page.goto("/health/")
        assert "ok" in page.locator("body").inner_text()

    def test_old_dashboard_url_lands_on_pipeline(self, page, e2e_login) -> None:
        page.goto("/dashboard/")
        assert page.url.endswith("/pipeline/screener/")
        assert page.get_by_role("link", name="Pipeline").count() >= 1

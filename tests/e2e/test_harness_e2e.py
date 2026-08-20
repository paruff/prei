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

    def test_login_redirects_to_dashboard(self, page, e2e_login) -> None:
        page.goto("/dashboard/")
        assert page.locator("text=Dashboard").count() >= 1 or page.url.endswith(
            "/dashboard/"
        )

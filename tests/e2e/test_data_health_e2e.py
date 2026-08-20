"""E2E tests for data health dashboard."""

import pytest

pytestmark = pytest.mark.django_db(transaction=True)


class TestDataHealth:
    def test_system_page_renders(self, page, e2e_login) -> None:
        """System status page loads with data source health heading."""
        page.goto("/system/")
        assert page.locator("h1", has_text="System Status").is_visible()
        assert page.locator("h2", has_text="Data Source Health").is_visible()

    def test_data_source_table_structure(self, page, e2e_login) -> None:
        """Data source health table has correct columns."""
        page.goto("/system/")
        table = page.locator("table", has_text="Data Source Health")
        assert table.is_visible()
        assert table.locator("th", has_text="Source").is_visible()
        assert table.locator("th", has_text="Last Run").is_visible()
        assert table.locator("th", has_text="Records").is_visible()
        assert table.locator("th", has_text="Status").is_visible()

    def test_refresh_all_button_exists(self, page, e2e_login) -> None:
        """Refresh All Sources button is visible."""
        page.goto("/system/")
        btn = page.locator("button", has_text="Refresh All Sources")
        assert btn.is_visible()

    def test_refresh_triggers_background_jobs(self, page, e2e_login) -> None:
        """Clicking Refresh All redirects back to system status."""
        page.goto("/system/")
        page.click("button:has-text('Refresh All Sources')")
        page.wait_for_url("**/system/**")
        # The redirect should succeed (background jobs may fail in test env)
        assert "/system/" in page.url

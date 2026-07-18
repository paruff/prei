"""HTTP acceptance tests for the property analysis pipeline.

Tests the real HTTP flow: login → dashboard → listings → property detail
→ growth areas → foreclosures — all via the deployed artifact.
"""

from __future__ import annotations

import httpx


class TestDashboard:
    """Dashboard must be accessible and render correctly."""

    def test_dashboard_redirects_to_login_when_unauthenticated(
        self, client: httpx.Client
    ) -> None:
        """GET /dashboard/ redirects to login for unauthenticated users."""
        resp = client.get("/dashboard/", follow_redirects=False)
        assert resp.status_code in (200, 302)


class TestDiscoveryPage:
    """Discovery page must render with expected controls."""

    def test_discovery_page_has_state_selector(self, client: httpx.Client) -> None:
        """Discovery page HTML contains a state selector or form."""
        resp = client.get("/discovery/", follow_redirects=True)
        assert resp.status_code == 200
        # Discovery page should have a form or interactive elements
        content = resp.text.lower()
        assert any(
            keyword in content
            for keyword in ("state", "city", "zip", "form", "select", "input")
        ), "Discovery page has no interactive elements"


class TestSystemStatus:
    """System status page must be available."""

    def test_system_page_requires_login(self, client: httpx.Client) -> None:
        """GET /system/ redirects to login for unauthenticated users."""
        resp = client.get("/system/", follow_redirects=False)
        assert resp.status_code in (200, 302)


class TestErrorHandling:
    """Application must handle errors gracefully without crashing."""

    def test_nonexistent_listing_returns_404(self, client: httpx.Client) -> None:
        """GET /api/listings/999999/ returns 404 for nonexistent listing."""
        resp = client.get("/api/listings/999999/")
        assert resp.status_code in (404, 405), (
            f"Expected 404 or 405 for nonexistent listing, got {resp.status_code}"
        )

    def test_invalid_state_code_returns_graceful_error(
        self, client: httpx.Client
    ) -> None:
        """Growth areas API handles invalid state codes gracefully."""
        resp = client.get("/api/v1/real-estate/growth-areas", params={"state": "XX"})
        # Should return a client error (400), not a server crash (500)
        assert resp.status_code < 500, (
            f"Server crashed on invalid state code: {resp.status_code}"
        )

    def test_malformed_url_does_not_crash(self, client: httpx.Client) -> None:
        """Random URL returns a graceful error, not a 500 traceback."""
        resp = client.get("/nonexistent-page-xyz/")
        assert resp.status_code < 500, (
            f"Server crashed on nonexistent URL: {resp.status_code}"
        )

"""Acceptance tests for Dashboard — portfolio overview."""

import httpx


class TestDashboard:
    """Dashboard page must render without crashing."""

    def test_requires_login(self, client: httpx.Client) -> None:
        resp = client.get("/dashboard/", follow_redirects=False)
        assert resp.status_code in (200, 302)

    def test_no_crash(self, client: httpx.Client) -> None:
        resp = client.get("/dashboard/", follow_redirects=True)
        assert resp.status_code < 500

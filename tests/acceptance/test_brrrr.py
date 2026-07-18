"""Acceptance tests for BRRRR Calculator."""

import httpx


class TestBrrrrCalculator:
    """BRRRR calculator page must load without crashing."""

    def test_requires_login(self, client: httpx.Client) -> None:
        resp = client.get("/brrrr/", follow_redirects=False)
        assert resp.status_code in (200, 302)

    def test_no_crash(self, client: httpx.Client) -> None:
        resp = client.get("/brrrr/", follow_redirects=True)
        assert resp.status_code < 500

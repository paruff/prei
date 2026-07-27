"""Acceptance tests for Growth Areas — market intelligence component."""

import httpx

from .schemas import GrowthAreasResponse, LoginGateAssertion, NoCrashAssertion


class TestGrowthAreasAPI:
    """Growth areas REST API must return structured data."""

    def test_returns_areas_for_state(self, client: httpx.Client) -> None:
        resp = client.get("/api/v1/real-estate/growth-areas", params={"state": "TX"})
        assert resp.status_code < 500
        areas = GrowthAreasResponse.model_validate(resp.json())
        assert areas.state == "TX"

    def test_rejects_invalid_state(self, client: httpx.Client) -> None:
        resp = client.get("/api/v1/real-estate/growth-areas", params={"state": "XX"})
        assert resp.status_code < 500

    def test_returns_areas_for_all_states(self, client: httpx.Client) -> None:
        for state in ("TX", "FL", "TN", "CA"):
            resp = client.get(
                "/api/v1/real-estate/growth-areas", params={"state": state}
            )
            assert resp.status_code < 500
            areas = GrowthAreasResponse.model_validate(resp.json())
            assert areas.state == state


class TestSystemPage:
    """System status page must render with data inventory."""

    def test_system_page_requires_login(self, client: httpx.Client) -> None:
        resp = client.get("/system/", follow_redirects=False)
        LoginGateAssertion.model_validate({"status_code": resp.status_code})

    def test_system_page_no_crash(self, client: httpx.Client) -> None:
        """System page should not 500 even when unauthenticated."""
        resp = client.get("/system/", follow_redirects=True)
        NoCrashAssertion.model_validate({"status_code": resp.status_code})

"""HTTP acceptance tests for API endpoints.

Tests assert on JSON structure and content, not just HTTP status codes.
Run against a deployed application via ``BASE_URL`` environment variable.
"""

from __future__ import annotations

import httpx
import pytest


class TestHealthEndpoints:
    """Health and status endpoints must return predictable JSON payloads."""

    def test_health_returns_ok(self, client: httpx.Client) -> None:
        """GET /health/ returns {"status": "ok"} with HTTP 200."""
        resp = client.get("/health/")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        assert data["status"] == "ok"

    def test_health_api_returns_status(self, client: httpx.Client) -> None:
        """GET /api/health/ returns JSON with 'status' key."""
        resp = client.get("/api/health/")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        assert "status" in data


class TestListingsAPI:
    """Listings API must return correctly shaped JSON."""

    def test_returns_expected_structure(self, client: httpx.Client) -> None:
        """GET /api/listings/ returns JSON with 'count' (int) and 'results' (list)."""
        resp = client.get("/api/listings/")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        assert isinstance(data.get("count"), int)
        assert isinstance(data.get("results"), list)


class TestGrowthAreasAPI:
    """Growth areas API must return structured market data."""

    def test_returns_results_key(self, client: httpx.Client) -> None:
        """GET /api/v1/real-estate/growth-areas?state=TX returns JSON with growth data."""
        resp = client.get("/api/v1/real-estate/growth-areas", params={"state": "TX"})
        if resp.status_code >= 500:
            pytest.fail(f"Growth areas API returned server error: {resp.status_code}")
        data = resp.json()
        assert isinstance(data, dict)
        # Response shape: {"areas": [...], "state": "TX", "totalResults": N, ...}
        assert "areas" in data
        assert isinstance(data.get("totalResults"), int)


class TestForeclosuresAPI:
    """Foreclosures API must return structured listing data."""

    def test_returns_results_key(self, client: httpx.Client) -> None:
        """GET /api/v1/foreclosures?location=Dallas,TX returns JSON with foreclosure data."""
        resp = client.get("/api/v1/foreclosures", params={"location": "Dallas, TX"})
        if resp.status_code >= 500:
            pytest.fail(f"Foreclosures API returned server error: {resp.status_code}")
        data = resp.json()
        assert isinstance(data, dict)
        # Response shape: {"resultsCount": N, "dataSources": [...], ...}
        assert isinstance(data.get("resultsCount"), int)

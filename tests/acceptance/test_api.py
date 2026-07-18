"""HTTP acceptance tests for API endpoints.

Tests assert on JSON structure and content using Pydantic schema validation,
not just HTTP status codes or loose dict access.
"""

from __future__ import annotations

import httpx
import pytest
from pydantic import ValidationError

from .schemas import (
    ForeclosuresResponse,
    GrowthAreasResponse,
    HealthResponse,
    ListingsResponse,
)


class TestHealthEndpoints:
    """Health and status endpoints must return predictable JSON payloads."""

    def test_health_returns_ok(self, client: httpx.Client) -> None:
        """GET /health/ returns {"status": "ok"} with HTTP 200."""
        resp = client.get("/health/")
        assert resp.status_code == 200
        health = HealthResponse.model_validate(resp.json())
        assert health.status == "ok"

    def test_health_api_returns_status(self, client: httpx.Client) -> None:
        """GET /api/health/ returns JSON with 'status' key."""
        resp = client.get("/api/health/")
        assert resp.status_code == 200
        health = HealthResponse.model_validate(resp.json())
        assert health.status == "ok"


class TestListingsAPI:
    """Listings API must return correctly shaped JSON."""

    def test_returns_valid_structure(self, client: httpx.Client) -> None:
        """GET /api/listings/ returns valid ListingsResponse."""
        resp = client.get("/api/listings/")
        assert resp.status_code == 200
        listings = ListingsResponse.model_validate(resp.json())
        assert isinstance(listings.count, int)
        assert isinstance(listings.results, list)

    def test_rejects_invalid_shape(self) -> None:
        """Pydantic validation catches malformed responses."""
        with pytest.raises(ValidationError):
            ListingsResponse.model_validate({"count": "not_an_int", "results": []})
        with pytest.raises(ValidationError):
            ListingsResponse.model_validate({"count": 0})  # missing results


class TestGrowthAreasAPI:
    """Growth areas API must return structured market data."""

    def test_returns_valid_structure(self, client: httpx.Client) -> None:
        """GET /api/v1/real-estate/growth-areas?state=TX returns valid response."""
        resp = client.get("/api/v1/real-estate/growth-areas", params={"state": "TX"})
        if resp.status_code >= 500:
            pytest.fail(f"Growth areas API returned server error: {resp.status_code}")
        areas = GrowthAreasResponse.model_validate(resp.json())
        assert areas.state == "TX"
        assert isinstance(areas.totalResults, int)
        assert isinstance(areas.areas, list)


class TestForeclosuresAPI:
    """Foreclosures API must return structured listing data."""

    def test_returns_valid_structure(self, client: httpx.Client) -> None:
        """GET /api/v1/foreclosures?location=Dallas,TX returns valid response."""
        resp = client.get("/api/v1/foreclosures", params={"location": "Dallas, TX"})
        if resp.status_code >= 500:
            pytest.fail(f"Foreclosures API returned server error: {resp.status_code}")
        fcls = ForeclosuresResponse.model_validate(resp.json())
        assert isinstance(fcls.resultsCount, int)
        assert isinstance(fcls.dataSources, list)

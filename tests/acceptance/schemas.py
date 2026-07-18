"""Pydantic models for response shape validation in acceptance tests.

Each model represents the expected JSON or document structure returned
by the deployed application. Tests use ``model_validate(resp.json())``
instead of raw dict access, catching type errors and missing keys at the
schema level rather than in individual assertions.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """GET /health/ and GET /api/health/ response."""

    status: str


class ListingsResponse(BaseModel):
    """GET /api/listings/ paginated response."""

    count: int
    results: list
    next: str | None = None
    previous: str | None = None


class GrowthAreasResponse(BaseModel):
    """GET /api/v1/real-estate/growth-areas response."""

    areas: list
    state: str
    totalResults: int


class ForeclosuresResponse(BaseModel):
    """GET /api/v1/foreclosures response."""

    resultsCount: int
    dataSources: list
    location: str


# ── HTML page assertions (not JSON, but used for content checks) ────────────


class LoginPageAssertion(BaseModel):
    """Assertions about the login page HTML response."""

    status_code: int = Field(ge=200, lt=400)
    has_password_input: bool
    content_is_html: bool


class DiscoveryPageAssertion(BaseModel):
    """Assertions about the discovery page HTML response."""

    status_code: int = Field(ge=200, lt=400)
    min_body_size: int = Field(gt=0)
    content_is_html: bool


class StaticAssetAssertion(BaseModel):
    """Assertions about static asset responses."""

    status_code: int = Field(ge=200, lt=400)
    content_type: str
    body_not_empty: bool

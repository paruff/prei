"""Pydantic models for response shape validation in acceptance tests.

Each model represents the expected JSON or document structure returned
by the deployed application. Tests use ``model_validate(resp.json())``
instead of raw dict access, catching type errors and missing keys at the
schema level rather than in individual assertions.
"""

from __future__ import annotations

from typing import Literal

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


class LoginGateAssertion(BaseModel):
    """A login-gated page either renders (200) or redirects to login (302)."""

    status_code: Literal[200, 302]


class NoCrashAssertion(BaseModel):
    """A page must respond without a server error, regardless of auth state."""

    status_code: int = Field(ge=200, lt=500)

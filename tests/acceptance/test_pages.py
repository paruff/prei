"""HTTP acceptance tests for HTML pages and static assets.

Tests assert on HTML DOM content using BeautifulSoup, not just HTTP
status codes.  Run against a deployed application via ``BASE_URL``.
"""

from __future__ import annotations

import httpx
from bs4 import BeautifulSoup


class TestLoginPage:
    """Login page must render a password input form."""

    def test_returns_html_with_password_field(self, client: httpx.Client) -> None:
        """GET /accounts/login/ returns HTML containing a password input."""
        resp = client.get("/accounts/login/")
        assert resp.status_code == 200
        # Assert content is HTML
        content_type = resp.headers.get("content-type", "")
        assert "text/html" in content_type

        soup = BeautifulSoup(resp.text, "html.parser")
        # Login form must have a password field
        password_input = soup.find("input", {"type": "password"})
        assert password_input is not None, (
            "Login page does not contain a password input field"
        )


class TestDiscoveryPage:
    """Discovery page must render with expected HTML structure."""

    def test_returns_html(self, client: httpx.Client) -> None:
        """GET /discovery/ returns HTML with HTTP 200."""
        resp = client.get("/discovery/", follow_redirects=True)
        assert resp.status_code == 200
        content_type = resp.headers.get("content-type", "")
        assert "text/html" in content_type

    def test_contains_expected_content(self, client: httpx.Client) -> None:
        """Discovery page body is non-trivial (not an empty shell)."""
        resp = client.get("/discovery/", follow_redirects=True)
        assert resp.status_code == 200
        # Response body should have meaningful HTML content
        assert len(resp.text) > 200, (
            "Discovery page returns minimal content — possible rendering error"
        )


class TestStaticAssets:
    """Static assets must be served with correct MIME types."""

    def test_css_served_with_correct_content_type(self, client: httpx.Client) -> None:
        """GET /static/css/base.css returns CSS with text/css Content-Type."""
        resp = client.get("/static/css/base.css")
        assert resp.status_code == 200
        content_type = resp.headers.get("content-type", "")
        assert "text/css" in content_type, (
            f"Expected text/css Content-Type, got: {content_type}"
        )
        assert len(resp.text) > 0, "CSS response body is empty"

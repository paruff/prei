"""HTTP acceptance tests for HTML pages and static assets.

Tests assert on HTML DOM content using BeautifulSoup, not just HTTP
status codes.  Run against a deployed application via ``BASE_URL``.
"""

from __future__ import annotations

import httpx
from bs4 import BeautifulSoup

from .schemas import DiscoveryPageAssertion, LoginPageAssertion, StaticAssetAssertion


class TestLoginPage:
    """Login page must render a password input form."""

    def test_returns_html_with_password_field(self, client: httpx.Client) -> None:
        """GET /accounts/login/ returns HTML containing a password input."""
        resp = client.get("/accounts/login/")
        content_type = resp.headers.get("content-type", "")

        soup = BeautifulSoup(resp.text, "html.parser")
        password_input = soup.find("input", {"type": "password"})

        page = LoginPageAssertion.model_validate(
            {
                "status_code": resp.status_code,
                "has_password_input": password_input is not None,
                "content_is_html": "text/html" in content_type,
            }
        )
        assert page.has_password_input, (
            "Login page does not contain a password input field"
        )
        assert page.content_is_html


class TestDiscoveryPage:
    """Discovery page must render with expected HTML structure."""

    def test_returns_html(self, client: httpx.Client) -> None:
        """GET /discovery/ returns HTML with HTTP 200."""
        resp = client.get("/discovery/", follow_redirects=True)
        content_type = resp.headers.get("content-type", "")

        page = DiscoveryPageAssertion.model_validate(
            {
                "status_code": resp.status_code,
                "min_body_size": len(resp.text),
                "content_is_html": "text/html" in content_type,
            }
        )
        assert page.status_code == 200
        assert page.content_is_html

    def test_contains_expected_content(self, client: httpx.Client) -> None:
        """Discovery page body is non-trivial (not an empty shell)."""
        resp = client.get("/discovery/", follow_redirects=True)

        page = DiscoveryPageAssertion.model_validate(
            {
                "status_code": resp.status_code,
                "min_body_size": len(resp.text),
                "content_is_html": "text/html" in resp.headers.get("content-type", ""),
            }
        )
        assert page.min_body_size > 200, (
            "Discovery page returns minimal content — possible rendering error"
        )


class TestStaticAssets:
    """Static assets must be served with correct MIME types."""

    def test_css_served_with_correct_content_type(self, client: httpx.Client) -> None:
        """GET /static/css/base.css returns CSS with text/css Content-Type."""
        resp = client.get("/static/css/base.css")
        content_type = resp.headers.get("content-type", "")

        asset = StaticAssetAssertion.model_validate(
            {
                "status_code": resp.status_code,
                "content_type": content_type,
                "body_not_empty": len(resp.text) > 0,
            }
        )
        assert "text/css" in asset.content_type, (
            f"Expected text/css Content-Type, got: {asset.content_type}"
        )
        assert asset.body_not_empty, "CSS response body is empty"

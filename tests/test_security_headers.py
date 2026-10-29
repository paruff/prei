"""FR9: Content-Security-Policy, Permissions-Policy, CORP and template CSP compliance."""

import re
from pathlib import Path

import pytest
from django.http import HttpResponse
from django.test import RequestFactory, override_settings

from core.middleware import SecurityHeadersMiddleware

TEMPLATES = Path(__file__).resolve().parent.parent / "templates"
NONCE_RE = re.compile(r"'nonce-([^']+)'")


def _nonce(response) -> str:
    match = NONCE_RE.search(response["Content-Security-Policy"])
    assert match is not None, "no nonce in Content-Security-Policy"
    return match.group(1)


def _directive(csp: str, name: str) -> str:
    for part in csp.split(";"):
        part = part.strip()
        if part.startswith(name + " "):
            return part
    raise AssertionError(f"{name} not in CSP: {csp}")


@pytest.mark.integration
class TestSecurityHeaders:
    @pytest.mark.parametrize(
        "path",
        [
            "/accounts/login/",
            "/dashboard/",
            "/no-such-page/",
            "/health/",
            "/static/manifest.json",
        ],
        ids=["html-200", "redirect", "404", "json", "static"],
    )
    def test_csp_on_every_response_kind(self, client, path):
        response = client.get(path)
        assert "Content-Security-Policy" in response.headers

    def test_nonce_only_script_and_style(self, client):
        csp = client.get("/accounts/login/")["Content-Security-Policy"]
        for name in ("script-src", "style-src"):
            directive = _directive(csp, name)
            assert "'nonce-" in directive
            assert "'unsafe-inline'" not in directive
        assert "frame-ancestors 'none'" in csp
        assert "object-src 'none'" in csp

    def test_header_nonce_matches_body_and_rotates(self, client):
        first = client.get("/accounts/login/")
        second = client.get("/accounts/login/")
        nonce1 = _nonce(first)
        nonce2 = _nonce(second)
        assert f'nonce="{nonce1}"' in first.content.decode()
        assert nonce1 != nonce2

    def test_permissions_policy_and_corp_present(self, client):
        response = client.get("/accounts/login/")
        assert "camera=()" in response["Permissions-Policy"]
        assert response["Cross-Origin-Resource-Policy"] == "same-origin"

    def test_security_headers_do_not_override_view_values(self):
        def view(request):
            return HttpResponse(
                "x", headers={"Cross-Origin-Resource-Policy": "cross-origin"}
            )

        response = SecurityHeadersMiddleware(view)(RequestFactory().get("/"))
        assert response["Cross-Origin-Resource-Policy"] == "cross-origin"
        assert "Permissions-Policy" in response

    def test_report_only_switches_header_name(self, client):
        from django.utils.csp import CSP

        policy = {"default-src": [CSP.SELF], "script-src": [CSP.SELF, CSP.NONCE]}
        with override_settings(SECURE_CSP=None, SECURE_CSP_REPORT_ONLY=policy):
            response = client.get("/accounts/login/")
        assert "Content-Security-Policy-Report-Only" in response.headers
        assert "Content-Security-Policy" not in response.headers


@pytest.mark.integration
class TestAuthenticatedPages:
    @pytest.mark.parametrize(
        "path", ["/dashboard/", "/growth-explorer/", "/pipeline/screening/settings/"]
    )
    def test_converted_pages_render_with_nonce(self, client, user, path):
        client.force_login(user)
        response = client.get(path)
        assert response.status_code == 200
        nonce = _nonce(response)
        assert f'nonce="{nonce}"' in response.content.decode()


def _template_files():
    return sorted(TEMPLATES.rglob("*.html"))


@pytest.mark.unit
class TestTemplateCspCompliance:
    def test_no_external_script_or_stylesheet(self):
        # AC9: nothing external remains, so no SRI is needed; any future one must carry integrity.
        offenders = []
        pattern = re.compile(
            r"<(?:script|link)\b[^>]*(?:src|href)=[\"'](https?:)?//[^>]*>", re.I
        )
        for path in _template_files():
            for tag in pattern.finditer(path.read_text()):
                if "integrity=" not in tag.group(0):
                    offenders.append(f"{path.name}: {tag.group(0)[:80]}")
        assert not offenders

    def test_every_script_and_style_block_has_nonce(self):
        pattern = re.compile(r"<(script|style)\b([^>]*)>", re.I)
        offenders = []
        for path in _template_files():
            for tag in pattern.finditer(path.read_text()):
                attrs = tag.group(2)
                if "src=" in attrs:
                    continue
                if 'nonce="{{ csp_nonce }}"' not in attrs:
                    offenders.append(f"{path.relative_to(TEMPLATES)}: {tag.group(0)}")
        assert not offenders

    def test_no_inline_handlers_style_attrs_or_javascript_urls(self):
        # Attributes must sit inside a tag so JS such as `var onePct = ...` is not flagged.
        pattern = re.compile(r"""<[a-z][^>]*\s(on[a-z]+|style)\s*=|javascript:""")
        offenders = []
        for path in _template_files():
            for line_no, line in enumerate(path.read_text().splitlines(), 1):
                if pattern.search(line):
                    offenders.append(f"{path.relative_to(TEMPLATES)}:{line_no}")
        assert not offenders

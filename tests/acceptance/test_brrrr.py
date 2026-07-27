"""Acceptance tests for BRRRR Calculator."""

import httpx

from .schemas import LoginGateAssertion, NoCrashAssertion


class TestBrrrrCalculator:
    """BRRRR calculator page must load without crashing."""

    def test_requires_login(self, client: httpx.Client) -> None:
        resp = client.get("/brrrr/", follow_redirects=False)
        LoginGateAssertion.model_validate({"status_code": resp.status_code})

    def test_no_crash(self, client: httpx.Client) -> None:
        resp = client.get("/brrrr/", follow_redirects=True)
        NoCrashAssertion.model_validate({"status_code": resp.status_code})

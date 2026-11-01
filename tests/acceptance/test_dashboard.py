"""Acceptance tests for Dashboard — portfolio overview."""

import httpx

from .schemas import LoginGateAssertion, NoCrashAssertion


class TestDashboard:
    """The old /dashboard/ URL redirects; the deal scores live at /pipeline/deals/."""

    def test_requires_login(self, client: httpx.Client) -> None:
        resp = client.get("/dashboard/", follow_redirects=False)
        LoginGateAssertion.model_validate({"status_code": resp.status_code})

    def test_no_crash(self, client: httpx.Client) -> None:
        resp = client.get("/pipeline/deals/", follow_redirects=True)
        NoCrashAssertion.model_validate({"status_code": resp.status_code})

"""Acceptance tests for Leasing Pipeline views."""

import httpx

from .schemas import LoginGateAssertion, NoCrashAssertion


class TestLeasingList:
    """Leasing list page must render."""

    def test_requires_login(self, client: httpx.Client) -> None:
        resp = client.get("/leasing/", follow_redirects=False)
        LoginGateAssertion.model_validate({"status_code": resp.status_code})

    def test_no_crash(self, client: httpx.Client) -> None:
        resp = client.get("/leasing/", follow_redirects=True)
        NoCrashAssertion.model_validate({"status_code": resp.status_code})


class TestLeasingKanban:
    """Leasing kanban board must render with columns."""

    def test_requires_login(self, client: httpx.Client) -> None:
        resp = client.get("/leasing/kanban/", follow_redirects=False)
        LoginGateAssertion.model_validate({"status_code": resp.status_code})

    def test_no_crash(self, client: httpx.Client) -> None:
        resp = client.get("/leasing/kanban/", follow_redirects=True)
        NoCrashAssertion.model_validate({"status_code": resp.status_code})

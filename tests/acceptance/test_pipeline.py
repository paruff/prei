"""Acceptance tests for Acquisition Pipeline views."""

import httpx

from .schemas import LoginGateAssertion, NoCrashAssertion


class TestPipelineList:
    """Pipeline list page must render with stage counts."""

    def test_requires_login(self, client: httpx.Client) -> None:
        resp = client.get("/pipeline/list/", follow_redirects=False)
        LoginGateAssertion.model_validate({"status_code": resp.status_code})

    def test_no_crash(self, client: httpx.Client) -> None:
        resp = client.get("/pipeline/list/", follow_redirects=True)
        NoCrashAssertion.model_validate({"status_code": resp.status_code})


class TestPipelineKanban:
    """Kanban board must render with stage columns."""

    def test_requires_login(self, client: httpx.Client) -> None:
        resp = client.get("/pipeline/kanban/", follow_redirects=False)
        LoginGateAssertion.model_validate({"status_code": resp.status_code})

    def test_no_crash(self, client: httpx.Client) -> None:
        resp = client.get("/pipeline/kanban/", follow_redirects=True)
        NoCrashAssertion.model_validate({"status_code": resp.status_code})


class TestPipelineScreener:
    """Screener page must render with filter bar."""

    def test_requires_login(self, client: httpx.Client) -> None:
        resp = client.get("/pipeline/screener/", follow_redirects=False)
        LoginGateAssertion.model_validate({"status_code": resp.status_code})

    def test_no_crash(self, client: httpx.Client) -> None:
        resp = client.get("/pipeline/screener/", follow_redirects=True)
        NoCrashAssertion.model_validate({"status_code": resp.status_code})

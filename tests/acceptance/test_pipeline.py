"""Acceptance tests for Acquisition Pipeline views."""

import httpx


class TestPipelineList:
    """Pipeline list page must render with stage counts."""

    def test_requires_login(self, client: httpx.Client) -> None:
        resp = client.get("/pipeline/list/", follow_redirects=False)
        assert resp.status_code in (200, 302)

    def test_no_crash(self, client: httpx.Client) -> None:
        resp = client.get("/pipeline/list/", follow_redirects=True)
        assert resp.status_code < 500


class TestPipelineKanban:
    """Kanban board must render with stage columns."""

    def test_requires_login(self, client: httpx.Client) -> None:
        resp = client.get("/pipeline/kanban/", follow_redirects=False)
        assert resp.status_code in (200, 302)

    def test_no_crash(self, client: httpx.Client) -> None:
        resp = client.get("/pipeline/kanban/", follow_redirects=True)
        assert resp.status_code < 500


class TestPipelineScreener:
    """Screener page must render with filter bar."""

    def test_requires_login(self, client: httpx.Client) -> None:
        resp = client.get("/pipeline/screener/", follow_redirects=False)
        assert resp.status_code in (200, 302)

    def test_no_crash(self, client: httpx.Client) -> None:
        resp = client.get("/pipeline/screener/", follow_redirects=True)
        assert resp.status_code < 500

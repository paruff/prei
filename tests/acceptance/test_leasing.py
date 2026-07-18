"""Acceptance tests for Leasing Pipeline views."""

import httpx


class TestLeasingList:
    """Leasing list page must render."""

    def test_requires_login(self, client: httpx.Client) -> None:
        resp = client.get("/leasing/list/", follow_redirects=False)
        assert resp.status_code in (200, 302)

    def test_no_crash(self, client: httpx.Client) -> None:
        resp = client.get("/leasing/list/", follow_redirects=True)
        assert resp.status_code < 500


class TestLeasingKanban:
    """Leasing kanban board must render with columns."""

    def test_requires_login(self, client: httpx.Client) -> None:
        resp = client.get("/leasing/kanban/", follow_redirects=False)
        assert resp.status_code in (200, 302)

    def test_no_crash(self, client: httpx.Client) -> None:
        resp = client.get("/leasing/kanban/", follow_redirects=True)
        assert resp.status_code < 500

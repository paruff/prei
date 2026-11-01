"""G7.2: the nav follows the journey (FR-18)."""

import re

import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="nav", password="pass")


def _nav(html):
    match = re.search(r"<nav class=\"topnav\".*?</nav>", html, flags=re.S)
    assert match
    return match.group(0)


def _link_texts(html):
    return [t.strip() for t in re.findall(r"<a [^>]*>(.*?)</a>", html, flags=re.S)]


def test_signed_in_nav_follows_the_journey(client, user):
    client.force_login(user)
    nav = _nav(client.get("/growth/").content.decode())
    texts = _link_texts(nav)
    assert texts[1:5] == ["Markets", "Pipeline", "Portfolio", "Leasing"]
    assert {"Investment Targets", "Screening", "System", "Sign out"} <= set(texts)
    assert 'aria-current="page"' in nav


def test_anonymous_sees_only_sign_in(client, db):
    nav = _nav(client.get("/accounts/login/").content.decode())
    assert _link_texts(nav)[1:] == ["Sign in"]


@pytest.mark.parametrize(
    "old,new",
    [("/dashboard/", "/pipeline/screener/"), ("/properties/", "/portfolio/")],
)
def test_folded_pages_redirect_to_their_homes(client, user, old, new):
    client.force_login(user)
    resp = client.get(old)
    assert resp.status_code == 302 and resp.url == new

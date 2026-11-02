"""Regression test for the Growth Area Explorer "Tier" selector.

The tier selector was previously wired on the client (POSTed to the server)
but never read by the view, and never linked to the state dropdown it sits
next to — selecting a tier had no visible effect. See core/views/__init__.py
growth_explorer() for the fix: the view now passes a state->tier mapping
that the template embeds via json_script for client-side filtering of the
state dropdown.
"""

from __future__ import annotations

import json
import re

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="growth_explorer_user",
        email="growth_explorer@test.com",
        password="testpass123",
    )


@pytest.fixture
def client(db, user):
    c = Client()
    c.force_login(user)
    return c


def test_growth_explorer_get_includes_state_tiers(client):
    """GET must embed a state->tier map the tier-select JS depends on."""
    response = client.get("/growth-explorer/")
    assert response.status_code == 200

    html = response.content.decode()
    match = re.search(r'id="state-tiers-data"[^>]*>(.*?)</script>', html, re.S)
    assert match is not None, "state-tiers-data json_script block missing"

    state_tiers = json.loads(match.group(1))
    # Known-good spot checks against core/services/landlord_data.py
    assert state_tiers["TX"] == "top"
    assert state_tiers["CA"] == "bottom"
    assert state_tiers["NY"] == "bottom"
    # Every US state/DC should have a tier (falls back to "middle" if unlisted)
    assert len(state_tiers) >= 50

    assert 'id="tier-select"' in html
    assert "applyTierFilter" in html

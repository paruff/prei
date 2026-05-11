"""BDD coverage for the happy-path property analysis workflow."""

from __future__ import annotations

import pytest
from pytest_bdd import given, scenario


@scenario(
    "../features/property_analysis.feature",
    "Investor adds a property and views KPIs",
)
@pytest.mark.django_db
def test_investor_workflow() -> None:
    """Run the happy-path investor workflow scenario."""


@given("I am logged in as an investor", target_fixture="logged_in_user")
def logged_in_user(db):
    """Create the authenticated investor used by the scenario."""
    from django.contrib.auth import get_user_model

    return get_user_model().objects.create_user(
        username="test_investor",
        password="pass",
    )

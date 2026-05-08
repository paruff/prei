from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from core.models import MarketSnapshot, Property, SharedProperty, Team, TeamMember
from core.services.collaboration import (
    add_note,
    get_team_properties,
    share_property_with_team,
)

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="owner", email="owner@example.com", password="pass1234"
    )


@pytest.fixture
def teammate(db):
    return User.objects.create_user(
        username="member", email="member@example.com", password="pass1234"
    )


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        username="other", email="other@example.com", password="pass1234"
    )


@pytest.fixture
def property_obj(user):
    return Property.objects.create(
        user=user,
        address="123 Team St",
        city="Austin",
        state="TX",
        zip_code="78701",
        purchase_price=Decimal("275000"),
    )


@pytest.fixture
def team(user, teammate):
    team_obj = Team.objects.create(name="Acquisition Team", owner=user)
    TeamMember.objects.create(team=team_obj, user=user, role=TeamMember.Role.OWNER)
    TeamMember.objects.create(team=team_obj, user=teammate, role=TeamMember.Role.MEMBER)
    return team_obj


@pytest.mark.django_db
def test_share_property_with_team_creates_shared_property(property_obj, team, user):
    shared = share_property_with_team(property_obj, team, user)

    assert isinstance(shared, SharedProperty)
    assert shared.property == property_obj
    assert shared.team == team
    assert shared.shared_by == user


@pytest.mark.django_db
def test_add_note_creates_property_note_with_author(property_obj, teammate):
    note = add_note(property_obj, teammate, "Great upside if rent comps hold.")

    assert note.property == property_obj
    assert note.author == teammate
    assert note.body == "Great upside if rent comps hold."


@pytest.mark.django_db
def test_get_team_properties_returns_only_shared_properties(property_obj, team, user):
    other_property = Property.objects.create(
        user=user,
        address="999 Solo Ave",
        city="Austin",
        state="TX",
        zip_code="78704",
        purchase_price=Decimal("310000"),
    )
    other_team = Team.objects.create(name="Other Team", owner=user)
    TeamMember.objects.create(team=other_team, user=user, role=TeamMember.Role.OWNER)

    share_property_with_team(property_obj, team, user)
    share_property_with_team(other_property, other_team, user)

    shared_ids = set(get_team_properties(team).values_list("id", flat=True))
    assert shared_ids == {property_obj.id}


@pytest.mark.django_db
def test_export_endpoint_returns_deal_pack_keys(property_obj, team, user, teammate):
    share_property_with_team(property_obj, team, user)
    add_note(property_obj, teammate, "Need updated insurance quote.")
    MarketSnapshot.objects.create(
        zip_code=property_obj.zip_code,
        city=property_obj.city,
        state=property_obj.state,
        rent_index=Decimal("2100.00"),
        price_trend=Decimal("0.0310"),
        crime_score=Decimal("3.20"),
        school_rating=Decimal("8.40"),
    )

    client = APIClient()
    client.force_authenticate(user=teammate)
    url = reverse(
        "api:export-property-deal-pack", kwargs={"property_id": property_obj.id}
    )
    response = client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert set(response.data.keys()) == {"property", "kpis", "notes", "marketSnapshot"}
    assert response.data["property"]["id"] == property_obj.id
    assert len(response.data["notes"]) == 1

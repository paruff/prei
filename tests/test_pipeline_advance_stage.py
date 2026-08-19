"""Tests for the "advance" action on pipeline_advance_stage.

Previously this view only handled action="hold" despite its name/docstring
claiming to advance stages. Property Discovery's results page now gives
passed-screening properties a "Continue to Underwriting" button that POSTs
here with action="advance" — this exercises that path end to end.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from django.utils import timezone

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="advance_stage_user",
        email="advance_stage@test.com",
        password="testpass123",
    )


@pytest.fixture
def client(db, user):
    c = Client()
    c.force_login(user)
    return c


@pytest.fixture
def screened_property(db, user):
    from core.models import PipelineProperty

    return PipelineProperty.objects.create(
        user=user,
        source_type="manual",
        source_id="advance-test",
        address="789 Advance Ave, Fort Worth TX 76102",
        address_hash="advance-hash",
        stage=PipelineProperty.Stage.SCREENING,
        status=PipelineProperty.Status.ACTIVE,
        screening_passed=True,
        price=Decimal("180000"),
        estimated_rent=Decimal("1600"),
        beds=3,
        discovered_at=timezone.now(),
        screening_at=timezone.now(),
    )


def test_advance_action_moves_to_next_stage(client, screened_property):
    from core.models import PipelineProperty

    url = reverse("pipeline_advance_stage", kwargs={"pk": screened_property.pk})
    response = client.post(url, {"action": "advance"})

    screened_property.refresh_from_db()
    assert screened_property.stage == PipelineProperty.Stage.UNDERWRITING
    assert screened_property.underwriting_at is not None
    assert response.status_code == 302


def test_advance_action_redirects_to_safe_next_url(client, screened_property):
    url = reverse("pipeline_advance_stage", kwargs={"pk": screened_property.pk})
    response = client.post(
        url, {"action": "advance", "next": "/discovery/?growth_area_id=1"}
    )
    assert response["Location"] == "/discovery/?growth_area_id=1"


def test_advance_action_ignores_unsafe_next_url(client, screened_property):
    url = reverse("pipeline_advance_stage", kwargs={"pk": screened_property.pk})
    response = client.post(
        url, {"action": "advance", "next": "https://evil.example.com/phish"}
    )
    assert response["Location"] != "https://evil.example.com/phish"


def test_hold_action_still_works(client, screened_property):
    from core.models import PipelineProperty

    url = reverse("pipeline_advance_stage", kwargs={"pk": screened_property.pk})
    client.post(url, {"action": "hold"})

    screened_property.refresh_from_db()
    assert screened_property.status == PipelineProperty.Status.ON_HOLD

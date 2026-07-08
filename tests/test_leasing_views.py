"""Tests for PIPE-11: Leasing pipeline views.

Tests cover:
- leasing_list: login required, shows entries, filters by status
- leasing_add: login, GET shows form, POST creates entry, pre-fill from property_id
- leasing_detail: login, 404 for non-owner, shows entry details
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="leasing_user",
        email="leasing@test.com",
        password="testpass123",
    )


@pytest.fixture
def client(db, user):
    c = Client()
    c.force_login(user)
    return c


@pytest.fixture
def owned_property(db, user):
    from core.models import Property as PropertyModel

    return PropertyModel.objects.create(
        user=user,
        address="123 Leasing Ln",
        city="Austin",
        state="TX",
        zip_code="78701",
        purchase_price=Decimal("250000"),
        purchase_date="2026-06-01",
        sqft=1500,
        monthly_rent_gross=Decimal("2000"),
    )


@pytest.fixture
def leasing_entry(db, user, owned_property):
    from core.models import LeasingPipelineProperty

    return LeasingPipelineProperty.objects.create(
        property_record=owned_property,
        user=user,
        asking_rent=Decimal("2200"),
        listed_date="2026-07-01",
        stage=LeasingPipelineProperty.Stage.LISTING,
        status=LeasingPipelineProperty.Status.ACTIVE,
    )


class TestLeasingList:
    def test_requires_login(self, db):
        c = Client()
        resp = c.get(reverse("leasing_list"))
        assert resp.status_code == 302
        assert "/login/" in resp.url

    def test_shows_entries(self, client, leasing_entry):
        resp = client.get(reverse("leasing_list"))
        assert resp.status_code == 200
        assert b"123 Leasing Ln" in resp.content

    def test_filters_by_status(self, client, user, owned_property, leasing_entry):
        from core.models import LeasingPipelineProperty

        # Create a FILLED entry
        LeasingPipelineProperty.objects.create(
            property_record=owned_property,
            user=user,
            status=LeasingPipelineProperty.Status.FILLED,
        )
        resp = client.get(reverse("leasing_list"), {"status": "FILLED"})
        assert resp.status_code == 200
        # Should show the filled entry
        assert b"pipeline-card" in resp.content

    def test_empty_state(self, client):
        resp = client.get(reverse("leasing_list"))
        assert resp.status_code == 200
        assert b"No leasing" in resp.content


class TestLeasingAdd:
    def test_requires_login(self, db):
        c = Client()
        resp = c.get(reverse("leasing_add"))
        assert resp.status_code == 302
        assert "/login/" in resp.url

    def test_get_shows_form(self, client, owned_property):
        resp = client.get(reverse("leasing_add"))
        assert resp.status_code == 200
        assert b"Select Property" in resp.content

    def test_post_creates_entry(self, client, owned_property):
        from core.models import LeasingPipelineProperty

        resp = client.post(
            reverse("leasing_add"),
            {
                "property_record": owned_property.pk,
                "asking_rent": "2300",
                "listed_date": "2026-07-15",
                "listing_source": "Zillow",
            },
        )
        assert resp.status_code == 302
        assert LeasingPipelineProperty.objects.filter(
            property_record=owned_property,
            asking_rent=Decimal("2300"),
        ).exists()

    def test_prefill_from_property_id(self, client, owned_property):
        url = reverse("leasing_add") + f"?property_id={owned_property.pk}"
        resp = client.get(url)
        assert resp.status_code == 200
        assert b"123 Leasing Ln" in resp.content


class TestLeasingDetail:
    def test_requires_login(self, db, leasing_entry):
        c = Client()
        url = reverse("leasing_detail", kwargs={"pk": leasing_entry.pk})
        resp = c.get(url)
        assert resp.status_code == 302
        assert "/login/" in resp.url

    def test_404_for_other_user(self, db, leasing_entry):
        other = User.objects.create_user(
            username="other_lease", email="other@test.com", password="pass"
        )
        c = Client()
        c.force_login(other)
        url = reverse("leasing_detail", kwargs={"pk": leasing_entry.pk})
        resp = c.get(url)
        assert resp.status_code == 404

    def test_shows_entry(self, client, leasing_entry):
        url = reverse("leasing_detail", kwargs={"pk": leasing_entry.pk})
        resp = client.get(url)
        assert resp.status_code == 200
        assert b"Asking Rent" in resp.content

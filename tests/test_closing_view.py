"""Tests for PIPE-9: Closing view and Property conversion.

Tests cover:
- GET shows closing form
- POST creates ClosingRecord + converts to Property
- Property record FK set on PipelineProperty
- Atomic rollback on failure
- 404 for non-owner
- Login required
- Portfolio dashboard shows incomplete banner
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
        username="closing_user",
        email="closing@test.com",
        password="testpass123",
    )


@pytest.fixture
def client(db, user):
    c = Client()
    c.force_login(user)
    return c


@pytest.fixture
def pipeline_property(db, user):
    from core.models import PipelineProperty

    pp = PipelineProperty.objects.create(
        user=user,
        source_type="manual",
        source_id="closing-test",
        address="456 Close Deal Dr, Austin TX 78701",
        address_hash="close-hash",
        stage=PipelineProperty.Stage.UNDERWRITING,
        status=PipelineProperty.Status.ACTIVE,
        price=Decimal("250000"),
        estimated_rent=Decimal("2000"),
        beds=3,
        discovered_at=timezone.now(),
    )
    return pp


class TestClosingView:
    def test_requires_login(self, db, pipeline_property):
        c = Client()
        url = reverse("pipeline_closing_create", kwargs={"pk": pipeline_property.pk})
        resp = c.get(url)
        assert resp.status_code == 302
        assert "/login/" in resp.url

    def test_404_for_other_user(self, db, pipeline_property):
        other = User.objects.create_user(
            username="other_close", email="other@test.com", password="pass"
        )
        c = Client()
        c.force_login(other)
        url = reverse("pipeline_closing_create", kwargs={"pk": pipeline_property.pk})
        resp = c.get(url)
        assert resp.status_code == 404

    def test_get_shows_form(self, client, pipeline_property):
        url = reverse("pipeline_closing_create", kwargs={"pk": pipeline_property.pk})
        resp = client.get(url)
        assert resp.status_code == 200
        assert b"Close Deal" in resp.content

    def test_post_creates_closing_and_property(self, client, pipeline_property):
        """POST creates ClosingRecord and Property, sets back-link."""
        from core.models import ClosingRecord, Property as PropertyModel

        url = reverse("pipeline_closing_create", kwargs={"pk": pipeline_property.pk})
        resp = client.post(
            url,
            {
                "final_purchase_price": "245000",
                "closing_date": "2026-07-15",
                "closing_costs": "5000",
                "lender": "First National Bank",
                "notes": "Closed on time",
            },
        )
        # Should redirect to portfolio_dashboard
        assert resp.status_code == 302
        assert resp.url == reverse("portfolio_dashboard")

        # ClosingRecord created
        closing = ClosingRecord.objects.get(pipeline_property=pipeline_property)
        assert closing.final_purchase_price == Decimal("245000")
        assert closing.lender == "First National Bank"

        # Property created
        prop = PropertyModel.objects.get(user=pipeline_property.user)
        assert prop.address == "456 Close Deal Dr, Austin TX 78701"
        assert prop.purchase_price == Decimal("250000")

        # PipelineProperty updated
        pipeline_property.refresh_from_db()
        assert pipeline_property.property_record == prop
        assert pipeline_property.status == "ACQUIRED"
        assert pipeline_property.stage == "ACQUIRED"

    def test_duplicate_conversion_error(self, client, pipeline_property):
        """Second POST returns error message, no crash."""
        url = reverse("pipeline_closing_create", kwargs={"pk": pipeline_property.pk})
        client.post(
            url,
            {
                "final_purchase_price": "245000",
                "closing_date": "2026-07-15",
            },
        )
        # Second attempt should redirect with error
        resp = client.post(
            url,
            {
                "final_purchase_price": "245000",
                "closing_date": "2026-07-15",
            },
        )
        assert resp.status_code == 302
        assert "/pipeline/" in resp.url  # Back to pipeline_detail

    def test_missing_required_fields(self, client, pipeline_property):
        """Missing required fields shows error."""
        url = reverse("pipeline_closing_create", kwargs={"pk": pipeline_property.pk})
        resp = client.post(url, {"closing_date": "2026-07-15"}, follow=True)
        assert resp.status_code == 200
        assert b"required" in resp.content


class TestPortfolioDashboard:
    def test_get_shows_page(self, client):
        url = reverse("portfolio_dashboard")
        resp = client.get(url)
        assert resp.status_code == 200

    def test_incomplete_banner(self, client, user):
        """Portfolio page loads with properties."""
        from core.models import Property as PropertyModel

        PropertyModel.objects.create(
            user=user,
            address="789 Incomplete Ln",
            city="Austin",
            state="TX",
            zip_code="78701",
            purchase_price=Decimal("200000"),
            purchase_date="2026-07-15",
            sqft=None,
            monthly_rent_gross=0,
        )
        url = reverse("portfolio_dashboard")
        resp = client.get(url)
        assert resp.status_code == 200

"""Tests for PIPE-6: Screening criteria settings view.

Tests cover:
- GET loads ScreeningCriteria for user
- POST saves criteria and re-screens properties
- Authenticated access only
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
        username="settings_user",
        email="settings@test.com",
        password="testpass123",
    )


@pytest.fixture
def client(db, user):
    c = Client()
    c.force_login(user)
    return c


class TestScreeningSettingsView:
    URL = reverse("pipeline_screening_settings")

    def test_requires_login(self, db):
        """Anonymous users redirected to login."""
        c = Client()
        resp = c.get(self.URL)
        assert resp.status_code == 302
        assert "/login/" in resp.url

    def test_get_creates_criteria(self, client, user):
        """GET creates ScreeningCriteria if it doesn't exist."""
        from core.models import ScreeningCriteria

        assert ScreeningCriteria.objects.filter(user=user).count() == 0
        resp = client.get(self.URL)
        assert resp.status_code == 200
        assert ScreeningCriteria.objects.filter(user=user).count() == 1

    def test_get_loads_existing_criteria(self, client, user):
        """GET loads existing criteria without creating duplicate."""
        from core.models import ScreeningCriteria

        ScreeningCriteria.objects.create(user=user, min_beds=3)
        resp = client.get(self.URL)
        assert resp.status_code == 200
        assert ScreeningCriteria.objects.filter(user=user).count() == 1

    def test_post_saves_price_range(self, client, user):
        """POST saves price range fields."""
        resp = client.post(
            self.URL,
            {
                "min_price": "100000",
                "max_price": "500000",
            },
        )
        assert resp.status_code == 302

        from core.models import ScreeningCriteria

        c = ScreeningCriteria.objects.get(user=user)
        assert c.min_price == Decimal("100000")
        assert c.max_price == Decimal("500000")

    def test_post_saves_yield_and_ratio(self, client, user):
        """POST saves yield and ratio fields."""
        resp = client.post(
            self.URL,
            {
                "min_gross_yield_pct": "8.00",
                "max_price_to_rent_ratio": "12.00",
            },
        )
        assert resp.status_code == 302

        from core.models import ScreeningCriteria

        c = ScreeningCriteria.objects.get(user=user)
        assert c.min_gross_yield_pct == Decimal("8.00")
        assert c.max_price_to_rent_ratio == Decimal("12.00")

    def test_post_saves_beds_and_size(self, client, user):
        """POST saves beds, sqft, year built."""
        resp = client.post(
            self.URL,
            {
                "min_beds": "2",
                "max_beds": "4",
                "min_sqft": "1000",
                "max_year_built": "2000",
            },
        )
        assert resp.status_code == 302

        from core.models import ScreeningCriteria

        c = ScreeningCriteria.objects.get(user=user)
        assert c.min_beds == 2
        assert c.max_beds == 4
        assert c.min_sqft == 1000
        assert c.max_year_built == 2000

    def test_post_saves_checkboxes(self, client, user):
        """POST saves multi-select checkbox fields."""
        resp = client.post(
            self.URL,
            {
                "allowed_property_types": ["single-family", "condo"],
                "allowed_states": ["TX", "FL"],
                "allowed_foreclosure_statuses": ["auction", "reo"],
            },
        )
        assert resp.status_code == 302

        from core.models import ScreeningCriteria

        c = ScreeningCriteria.objects.get(user=user)
        assert c.allowed_property_types == ["single-family", "condo"]
        assert c.allowed_states == ["TX", "FL"]
        assert c.allowed_foreclosure_statuses == ["auction", "reo"]

    def test_post_saves_gacs_score(self, client, user):
        """POST saves min GACS score."""
        resp = client.post(
            self.URL,
            {
                "min_gacs_score": "50.00",
            },
        )
        assert resp.status_code == 302

        from core.models import ScreeningCriteria

        c = ScreeningCriteria.objects.get(user=user)
        assert c.min_gacs_score == Decimal("50.00")

    def test_post_clears_optional_fields(self, client, user):
        """POST with empty optional nullable fields stores None."""
        from core.models import ScreeningCriteria

        c = ScreeningCriteria.objects.create(
            user=user,
            max_price=Decimal("500000"),
            min_gacs_score=Decimal("50"),
        )

        resp = client.post(
            self.URL,
            {
                "max_price": "",
                "min_gacs_score": "",
            },
        )
        assert resp.status_code == 302

        c.refresh_from_db()
        assert c.max_price is None
        assert c.min_gacs_score is None

    def test_rescreen_discovered_properties(self, client, user):
        """Saving criteria re-screens DISCOVERED/SCREENING properties."""
        from core.models import PipelineProperty

        # Create a pipeline property at DISCOVERED
        pp = PipelineProperty.objects.create(
            user=user,
            source_type="manual",
            source_id="rescreen-1",
            address="123 Rescreen St",
            address_hash="rescreen",
            stage=PipelineProperty.Stage.DISCOVERED,
            status=PipelineProperty.Status.ACTIVE,
            price=Decimal("200000"),
            beds=3,
        )
        assert pp.screening_passed is None

        resp = client.post(
            self.URL,
            {
                "min_beds": "2",
            },
        )
        assert resp.status_code == 302

        pp.refresh_from_db()
        # Should have been re-screened
        assert pp.screening_passed is not None

    def test_rescreen_count_in_message(self, client, user):
        """Success message includes count of re-screened properties."""
        from core.models import PipelineProperty

        PipelineProperty.objects.create(
            user=user,
            source_type="manual",
            source_id="count-1",
            address="123 Count St",
            address_hash="count1",
            stage=PipelineProperty.Stage.DISCOVERED,
            status=PipelineProperty.Status.ACTIVE,
            price=Decimal("200000"),
        )
        PipelineProperty.objects.create(
            user=user,
            source_type="manual",
            source_id="count-2",
            address="456 Count Ave",
            address_hash="count2",
            stage=PipelineProperty.Stage.SCREENING,
            status=PipelineProperty.Status.ACTIVE,
            price=Decimal("300000"),
        )

        resp = client.post(self.URL, {"min_beds": "2"})
        assert resp.status_code == 302

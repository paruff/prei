"""Tests for PIPE-5: Add to Pipeline from VRM list view.

Tests cover:
- Adding VRM property creates PipelineProperty, runs screening, redirects
- Adding same VRM property twice returns existing record, no duplicate
- POST only — GET returns error
- Unknown source_type returns error
- Missing source_id returns error
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
        username="pipe5",
        email="pipe5@test.com",
        password="testpass123",
    )


@pytest.fixture
def client(db, user):
    c = Client()
    c.force_login(user)
    return c


@pytest.fixture
def vrm_property(db):
    """VrmProperty fixture for add-to-pipeline tests."""
    from core.models import VrmProperty as VP

    now = timezone.now()
    vp = VP(
        vrm_property_id=5001,
        vrm_listing_url="https://example.com/5001",
        address="5001 Pipeline Ave",
        city="Austin",
        state="TX",
        zip_code="78701",
        list_price=Decimal("250000"),
        projected_monthly_rent=Decimal("2000"),
        bedrooms=3,
        year_built=2010,
        property_type="single-family",
        status=VP.Status.FOR_SALE,
        scraped_at=now,
        last_seen_at=now,
    )
    vp.save()
    return vp


class TestAddToPipelineView:
    URL = reverse("pipeline_add_from_source")

    def test_requires_login(self, db, vrm_property):
        """Anonymous users are redirected to login."""
        c = Client()
        resp = c.post(
            self.URL,
            {"source_type": "vrm", "source_id": "5001"},
        )
        assert resp.status_code == 302
        assert "/login/" in resp.url

    def test_get_returns_error(self, client):
        """GET request returns error and redirects to pipeline_list."""
        resp = client.get(self.URL)
        assert resp.status_code == 302
        assert "/pipeline/list/" in resp.url

    def test_adds_vrm_to_pipeline(self, client, user, vrm_property):
        """POST with valid source creates PipelineProperty and redirects to detail."""
        from core.models import PipelineProperty

        resp = client.post(
            self.URL,
            {"source_type": "vrm", "source_id": "5001"},
        )
        # Should redirect to pipeline_detail
        assert resp.status_code == 302
        detail_url = reverse("pipeline_detail", kwargs={"pk": 1})
        assert detail_url in resp.url

        # PipelineProperty should exist
        pp = PipelineProperty.objects.get(user=user, source_type="vrm")
        assert pp.source_id == "5001"
        assert pp.stage == "SCREENING"  # create_from_vrm runs screening
        assert pp.screening_passed is not None

    def test_duplicate_returns_existing(self, client, user, vrm_property):
        """Adding same VRM property twice returns existing record."""
        from core.models import PipelineProperty

        # First add
        client.post(self.URL, {"source_type": "vrm", "source_id": "5001"})
        count_after_first = PipelineProperty.objects.count()

        # Second add
        resp = client.post(self.URL, {"source_type": "vrm", "source_id": "5001"})
        count_after_second = PipelineProperty.objects.count()

        assert count_after_first == 1
        assert count_after_second == 1  # No duplicate
        assert resp.status_code == 302

        # Should redirect to existing detail page
        pp = PipelineProperty.objects.get(user=user, source_type="vrm")
        detail_url = reverse("pipeline_detail", kwargs={"pk": pp.pk})
        assert detail_url in resp.url

    def test_unknown_source_type(self, client):
        """Unknown source_type returns error and redirects."""
        resp = client.post(
            self.URL,
            {"source_type": "bogus", "source_id": "1"},
        )
        assert resp.status_code == 302

    def test_missing_source_id(self, client):
        """Missing source_id returns error and redirects."""
        resp = client.post(
            self.URL,
            {"source_type": "vrm", "source_id": ""},
        )
        assert resp.status_code == 302

    def test_nonexistent_vrm_id(self, client):
        """Nonexistent VRM ID returns error and redirects."""
        resp = client.post(
            self.URL,
            {"source_type": "vrm", "source_id": "999999"},
        )
        assert resp.status_code == 302

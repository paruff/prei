"""Tests for PIPE-8: Offer, DD, and Renovation forms + views.

Tests cover:
- Offer creation and listing
- DD checklist save and no-go kill
- Renovation record save
- 404 for non-owner access
- Login required
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
        username="pipe8",
        email="pipe8@test.com",
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
        source_id="pipe8-test",
        address="123 Pipeline Ave, Austin TX 78701",
        address_hash="pipe8-hash",
        stage=PipelineProperty.Stage.DISCOVERED,
        status=PipelineProperty.Status.ACTIVE,
        price=Decimal("250000"),
        beds=3,
        discovered_at=timezone.now(),
    )
    return pp


class TestOfferCreate:
    def test_requires_login(self, db, pipeline_property):
        c = Client()
        url = reverse("pipeline_offer_create", kwargs={"pk": pipeline_property.pk})
        resp = c.get(url)
        assert resp.status_code == 302
        assert "/login/" in resp.url

    def test_404_for_other_user(self, db, pipeline_property):
        other = User.objects.create_user(
            username="other", email="other@test.com", password="pass"
        )
        c = Client()
        c.force_login(other)
        url = reverse("pipeline_offer_create", kwargs={"pk": pipeline_property.pk})
        resp = c.get(url)
        assert resp.status_code == 404

    def test_get_shows_form(self, client, pipeline_property):
        url = reverse("pipeline_offer_create", kwargs={"pk": pipeline_property.pk})
        resp = client.get(url)
        assert resp.status_code == 200
        assert b"Offer" in resp.content

    def test_post_creates_offer(self, client, pipeline_property):
        from core.models import OfferRecord

        url = reverse("pipeline_offer_create", kwargs={"pk": pipeline_property.pk})
        resp = client.post(
            url,
            {
                "offer_price": "300000",
                "offer_date": "2026-07-10",
                "contingencies": ["inspection", "financing"],
                "notes": "Initial offer",
            },
        )
        assert resp.status_code == 302
        assert (
            OfferRecord.objects.filter(pipeline_property=pipeline_property).count() == 1
        )

    def test_list_existing_offers(self, client, pipeline_property):
        from core.models import OfferRecord

        OfferRecord.objects.create(
            pipeline_property=pipeline_property,
            offer_price=Decimal("300000"),
            offer_date="2026-07-10",
        )
        url = reverse("pipeline_offer_create", kwargs={"pk": pipeline_property.pk})
        resp = client.get(url)
        assert resp.status_code == 200
        assert b"300,000" in resp.content or b"300000" in resp.content


class TestDDChecklist:
    def test_get_shows_form(self, client, pipeline_property):
        url = reverse("pipeline_dd_checklist", kwargs={"pk": pipeline_property.pk})
        resp = client.get(url)
        assert resp.status_code == 200
        assert b"Go / No-Go" in resp.content

    def test_post_saves_checklist(self, client, pipeline_property):
        from core.models import DueDiligenceChecklist

        url = reverse("pipeline_dd_checklist", kwargs={"pk": pipeline_property.pk})
        resp = client.post(
            url,
            {
                "inspection_scheduled": "1",
                "title_search_ordered": "1",
                "go_no_go": "pending",
            },
        )
        assert resp.status_code == 302
        dd = DueDiligenceChecklist.objects.get(pipeline_property=pipeline_property)
        assert dd.inspection_scheduled is True
        assert dd.title_search_ordered is True

    def test_no_go_kills_property(self, client, pipeline_property):

        url = reverse("pipeline_dd_checklist", kwargs={"pk": pipeline_property.pk})
        resp = client.post(
            url,
            {
                "go_no_go": "no_go",
                "no_go_reason": "Failed inspection — foundation issues",
            },
        )
        assert resp.status_code == 302
        pipeline_property.refresh_from_db()
        assert pipeline_property.status == "KILLED"
        assert "foundation" in pipeline_property.kill_reason


class TestRenovation:
    def test_get_shows_form(self, client, pipeline_property):
        url = reverse("pipeline_renovation", kwargs={"pk": pipeline_property.pk})
        resp = client.get(url)
        assert resp.status_code == 200
        assert b"Renovation" in resp.content

    def test_post_saves_renovation(self, client, pipeline_property):
        from core.models import RenovationRecord

        url = reverse("pipeline_renovation", kwargs={"pk": pipeline_property.pk})
        resp = client.post(
            url,
            {
                "estimated_budget": "35000",
                "contractor": "ABC Remodeling",
                "scope_of_work": "Kitchen and bathroom renovation",
                "status": "in_progress",
                "start_date": "2026-08-01",
            },
        )
        assert resp.status_code == 302
        ren = RenovationRecord.objects.get(pipeline_property=pipeline_property)
        assert ren.estimated_budget == Decimal("35000")
        assert ren.contractor == "ABC Remodeling"
        assert ren.status == "in_progress"

    def test_complete_shows_leasing_link(self, client, pipeline_property):
        from core.models import RenovationRecord

        RenovationRecord.objects.create(
            pipeline_property=pipeline_property,
            estimated_budget=Decimal("35000"),
            status="complete",
        )
        url = reverse("pipeline_renovation", kwargs={"pk": pipeline_property.pk})
        resp = client.get(url)
        assert resp.status_code == 200
        assert b"Leasing" in resp.content

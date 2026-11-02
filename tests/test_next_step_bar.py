"""G7.3 (FR-18): an acquired property's detail page links to its next steps."""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from core.models import PipelineProperty, Property

User = get_user_model()


@pytest.fixture
def acquired(db, client):
    user = User.objects.create_user(username="nsb", password="pw")
    client.force_login(user)
    record = Property.objects.create(
        user=user,
        address="9 Next Step Ln",
        purchase_price=Decimal("210000"),
        monthly_rent_gross=Decimal("1750"),
    )
    return PipelineProperty.objects.create(
        user=user,
        source_type="manual",
        source_id="nsb",
        address=record.address,
        address_hash="nsb-hash",
        stage=PipelineProperty.Stage.ACQUIRED,
        status=PipelineProperty.Status.ACQUIRED,
        discovered_at=timezone.now(),
        property_record=record,
    )


def test_bar_links_to_the_three_next_steps(client, acquired):
    pid = acquired.property_record_id
    html = client.get(reverse("pipeline_detail", args=[acquired.pk])).content.decode()
    assert f"/portfolio/?property_id={pid}#enter-actuals" in html
    assert f"/leasing/add/?property_id={pid}" in html
    assert "/brrrr/?purchase_price=210000.00&amp;monthly_rent=1750.00" in html


def test_bar_hidden_before_acquisition(client, acquired):
    acquired.status = PipelineProperty.Status.ACTIVE
    acquired.save()
    html = client.get(reverse("pipeline_detail", args=[acquired.pk])).content.decode()
    assert "data-next-steps" not in html


def test_brrrr_and_actuals_are_prefilled(client, acquired):
    brrrr = client.get(
        reverse("brrrr_calculator"),
        {"purchase_price": "210000.00", "monthly_rent": "1750.00"},
    )
    assert 'value="210000.00"' in brrrr.content.decode()
    assert 'value="1750.00"' in brrrr.content.decode()
    junk = client.get(
        reverse("brrrr_calculator"), {"purchase_price": "x", "monthly_rent": "NaN"}
    )
    assert 'value="120000"' in junk.content.decode()
    pid = acquired.property_record_id
    dash = client.get(reverse("portfolio_dashboard"), {"property_id": pid})
    assert f'<option value="{pid}" selected>' in dash.content.decode()

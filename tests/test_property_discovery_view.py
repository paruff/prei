"""End-to-end test for the Property Discovery AJAX conversion + per-property CTAs.

Discovery previously did a blocking synchronous <form method="post"> with no
progress feedback past an initial flash, and results only offered a generic
"View in Screener" link even though screening already ran server-side.
This exercises the real POST path (HUD source) and checks the rendered
results block: per-property rows, a "Continue to Underwriting" CTA for
passed properties pointing at a real reversible URL, and the swappable
#results-section wrapper the JS fetch() handler depends on.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="discovery_view_user",
        email="discovery_view@test.com",
        password="testpass123",
    )


@pytest.fixture
def client(db, user):
    c = Client()
    c.force_login(user)
    return c


@pytest.fixture
def growth_area(db):
    from core.models import GrowthArea

    return GrowthArea.objects.create(
        state="TX",
        city_name="Discoveryville",
        metro_area="Discoveryville",
        population_growth_rate=Decimal("0.0100"),
        employment_growth_rate=Decimal("0.0200"),
        median_income_growth=Decimal("0.0300"),
        housing_demand_index=50,
        data_timestamp=timezone.now(),
    )


@pytest.fixture
def hud_property(growth_area):
    from core.models import HudProperty

    return HudProperty.objects.create(
        hud_case_number="DISC-TEST-1",
        address="1 Discovery Ln",
        city=growth_area.city_name,
        state=growth_area.state,
        zip_code="76102",
        asking_price=Decimal("120000"),
        list_price=Decimal("120000"),
        status=HudProperty.Status.ACTIVE,
        scraped_at=timezone.now(),
        last_seen_at=timezone.now(),
    )


def test_discovery_post_renders_per_property_results(
    client, user, growth_area, hud_property
):
    response = client.post(
        f"/discovery/?growth_area_id={growth_area.pk}",
        {"growth_area_id": growth_area.pk, "sources": ["hud"]},
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )
    assert response.status_code == 200

    html = response.content.decode()
    assert 'id="results-section"' in html
    assert hud_property.address in html

    from core.models import PipelineProperty

    pp = PipelineProperty.objects.get(user=user, growth_area=growth_area)
    advance_url = f"/pipeline/{pp.pk}/advance/"

    if pp.screening_passed:
        assert "Continue to Underwriting" in html
        assert advance_url in html
    else:
        assert f"/pipeline/{pp.pk}/" in html

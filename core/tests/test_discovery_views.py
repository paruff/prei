"""Acceptance tests for HUD/USDA property list/detail views and Add to Pipeline."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from core.models import (
    HudProperty,
    PipelineProperty,
    ScreeningCriteria,
    UsdaProperty,
)

UserModel = get_user_model()


@pytest.fixture
def user() -> UserModel:  # type: ignore[valid-type]
    return UserModel.objects.create_user(
        username="discovery_user",
        password="testpass",
    )


@pytest.fixture
def criteria(user: UserModel) -> ScreeningCriteria:  # type: ignore[valid-type]
    return ScreeningCriteria.objects.create(
        user=user,
        allowed_states=["TX"],
        min_price=Decimal("50000"),
        max_price=Decimal("500000"),
    )


@pytest.fixture
def hud_prop() -> HudProperty:
    return HudProperty.objects.create(
        hud_case_number="HUD-PIPELINE-001",
        address="111 Pipeline Dr",
        city="Austin",
        state="TX",
        zip_code="78701",
        asking_price=Decimal("150000"),
        status=HudProperty.Status.ACTIVE,
        scraped_at=timezone.now(),
        last_seen_at=timezone.now(),
    )


@pytest.fixture
def usda_prop() -> UsdaProperty:
    return UsdaProperty.objects.create(
        usda_case_number="USDA-PIPELINE-001",
        address="222 Rural Rd",
        city="Dallas",
        state="TX",
        zip_code="75201",
        list_price=Decimal("180000"),
        status=UsdaProperty.Status.ACTIVE,
        scraped_at=timezone.now(),
        last_seen_at=timezone.now(),
    )


# ═══════════════════════════════════════════════════════════════════════════
# HUD list view
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.django_db
def test_hud_list_view_returns_200(
    client: Any,
    user: UserModel,  # type: ignore[valid-type]
    hud_prop: HudProperty,
) -> None:
    """HUD property list view returns 200 for authenticated user."""
    client.force_login(user)
    response = client.get(reverse("hud_property_list"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_hud_add_to_pipeline_creates_pipeline_property(
    client: Any,
    user: UserModel,  # type: ignore[valid-type]
    hud_prop: HudProperty,
    criteria: ScreeningCriteria,
) -> None:
    """Add to Pipeline POST creates PipelineProperty with source_type='hud'."""
    client.force_login(user)
    response = client.post(
        reverse("pipeline_add_from_source"),
        {
            "source_type": "hud",
            "source_id": hud_prop.hud_case_number,
        },
    )

    # Should redirect to pipeline detail
    assert response.status_code == 302

    assert PipelineProperty.objects.filter(
        source_type="hud",
        source_id=hud_prop.hud_case_number,
        user=user,
    ).exists()


# ═══════════════════════════════════════════════════════════════════════════
# USDA list view
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.django_db
def test_usda_list_view_returns_200(
    client: Any,
    user: UserModel,  # type: ignore[valid-type]
    usda_prop: UsdaProperty,
) -> None:
    """USDA property list view returns 200 for authenticated user."""
    client.force_login(user)
    response = client.get(reverse("usda_property_list"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_usda_add_to_pipeline_creates_pipeline_property(
    client: Any,
    user: UserModel,  # type: ignore[valid-type]
    usda_prop: UsdaProperty,
    criteria: ScreeningCriteria,
) -> None:
    """Add to Pipeline POST creates PipelineProperty with source_type='usda'."""
    client.force_login(user)
    response = client.post(
        reverse("pipeline_add_from_source"),
        {
            "source_type": "usda",
            "source_id": usda_prop.usda_case_number,
        },
    )

    assert response.status_code == 302

    assert PipelineProperty.objects.filter(
        source_type="usda",
        source_id=usda_prop.usda_case_number,
        user=user,
    ).exists()

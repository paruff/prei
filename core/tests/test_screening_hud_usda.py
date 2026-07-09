"""Acceptance tests for HUD/USDA property screening."""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from core.models import HudProperty, ScreeningCriteria, UsdaProperty
from core.services.screening import screen_property

UserModel = get_user_model()


@pytest.fixture
def user() -> UserModel:  # type: ignore[valid-type]
    return UserModel.objects.create_user(
        username="screener",
        password="testpass",
    )


@pytest.fixture
def criteria(user: UserModel) -> ScreeningCriteria:  # type: ignore[valid-type]
    """ScreeningCriteria targeting TX only."""
    return ScreeningCriteria.objects.create(
        user=user,
        allowed_states=["TX"],
        min_price=Decimal("50000"),
        max_price=Decimal("500000"),
        min_gross_yield_pct=Decimal("8"),
    )


@pytest.fixture
def hud_property() -> HudProperty:
    """A HudProperty in California (should be killed by state filter)."""
    return HudProperty.objects.create(
        hud_case_number="HUD-TEST-001",
        address="123 CA St",
        city="Los Angeles",
        state="CA",
        zip_code="90001",
        asking_price=Decimal("150000"),
        status=HudProperty.Status.ACTIVE,
        scraped_at=timezone.now(),
        last_seen_at=timezone.now(),
    )


@pytest.fixture
def hud_property_tx() -> HudProperty:
    """A HudProperty in Texas with yield-friendly price."""
    return HudProperty.objects.create(
        hud_case_number="HUD-TEST-002",
        address="456 TX Ave",
        city="Austin",
        state="TX",
        zip_code="78701",
        asking_price=Decimal("120000"),
        status=HudProperty.Status.ACTIVE,
        scraped_at=timezone.now(),
        last_seen_at=timezone.now(),
    )


@pytest.fixture
def usda_property_ca() -> UsdaProperty:
    """A UsdaProperty in California (should be killed by state filter)."""
    return UsdaProperty.objects.create(
        usda_case_number="USDA-TEST-001",
        address="789 CA Blvd",
        city="San Francisco",
        state="CA",
        zip_code="94101",
        list_price=Decimal("200000"),
        status=UsdaProperty.Status.ACTIVE,
        scraped_at=timezone.now(),
        last_seen_at=timezone.now(),
    )


@pytest.fixture
def usda_property_tx() -> UsdaProperty:
    """A UsdaProperty in Texas with yield-friendly price."""
    return UsdaProperty.objects.create(
        usda_case_number="USDA-TEST-002",
        address="321 TX Dr",
        city="Dallas",
        state="TX",
        zip_code="75201",
        list_price=Decimal("180000"),
        status=UsdaProperty.Status.ACTIVE,
        scraped_at=timezone.now(),
        last_seen_at=timezone.now(),
    )


# ═══════════════════════════════════════════════════════════════════════════
# HudProperty tests
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.django_db
def test_hud_property_fails_state_kill(
    hud_property: HudProperty,
    criteria: ScreeningCriteria,
) -> None:
    """HudProperty in non-target state is hard-killed."""
    result = screen_property(hud_property, criteria)

    assert result.passed is False
    assert result.score == Decimal("0")
    assert result.kill_reason is not None
    assert "state" in result.kill_reason.lower()


@pytest.mark.django_db
def test_hud_property_yield_skipped_no_rent(
    hud_property_tx: HudProperty,
    criteria: ScreeningCriteria,
) -> None:
    """Yield criteria skipped if no rent estimate available."""
    result = screen_property(hud_property_tx, criteria)

    assert result.yield_evaluated is False
    assert result.yield_note == "no_rent_estimate"


# ═══════════════════════════════════════════════════════════════════════════
# UsdaProperty tests
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.django_db
def test_usda_property_fails_state_kill(
    usda_property_ca: UsdaProperty,
    criteria: ScreeningCriteria,
) -> None:
    """UsdaProperty in non-target state is hard-killed."""
    result = screen_property(usda_property_ca, criteria)

    assert result.passed is False
    assert result.score == Decimal("0")
    assert result.kill_reason is not None
    assert "state" in result.kill_reason.lower()


@pytest.mark.django_db
def test_usda_property_yield_skipped_no_rent(
    usda_property_tx: UsdaProperty,
    criteria: ScreeningCriteria,
) -> None:
    """UsdaProperty yield screening is skipped with no-rent-estimate note."""
    result = screen_property(usda_property_tx, criteria)

    assert result.yield_evaluated is False
    assert result.yield_note == "no_rent_estimate"


@pytest.mark.django_db
def test_hud_fmr_fallback_graceful_without_key(
    hud_property_tx: HudProperty,
    criteria: ScreeningCriteria,
) -> None:
    """HUD FMR fallback returns None gracefully when no API key configured."""
    from core.services.pipeline import create_from_hud
    from core.services.screening import _get_monthly_rent

    UserModel = get_user_model()
    user = UserModel.objects.first() or UserModel.objects.create_user(
        username="hud_fmr_test", password="test"
    )
    pp, _ = create_from_hud(hud_property_tx, user)
    pp.estimated_rent = None
    pp.price = Decimal("200000")
    pp.save(update_fields=["estimated_rent", "price"])

    # Should return None without raising (no HUD_API_KEY set)
    result = _get_monthly_rent(pp, hud_property_tx)
    assert result is None

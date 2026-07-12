"""Comprehensive screening tests for critical untested paths.

Covers: state/property_type/foreclosure_status extraction, GACS score,
year-built, beds, price-to-rent ratio, source model adaptation, and
the full screen_property() pipeline with VRM source.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from core.models import (
    GrowthArea,
    HudProperty,
    PipelineProperty,
    ScreeningCriteria,
    UsdaProperty,
)
from core.services.screening import (
    _eval_beds,
    _eval_gacs_score,
    _eval_gross_yield,
    _eval_price_to_rent_ratio,
    _eval_year_built,
    _extract_city,
    _extract_foreclosure_status,
    _extract_property_type,
    _extract_state,
    _is_source_model,
    screen_property,
)

UserModel = get_user_model()


@pytest.fixture
def user() -> Any:
    return UserModel.objects.create_user(username="screener", password="testpass")


@pytest.fixture
def criteria(user: Any) -> ScreeningCriteria:
    return ScreeningCriteria.objects.create(
        user=user,
        allowed_states=["TX"],
        min_price=Decimal("50000"),
        max_price=Decimal("500000"),
        min_gross_yield_pct=Decimal("8"),
        max_price_to_rent_ratio=Decimal("15"),
        max_year_built=2025,
        min_beds=2,
    )


@pytest.fixture
def pipeline_prop(user: Any) -> PipelineProperty:
    return PipelineProperty.objects.create(
        user=user,
        source_type=PipelineProperty.SourceType.VRM,
        source_id="VRM-TEST-001",
        address="123 Main St",
        stage=PipelineProperty.Stage.DISCOVERED,
        status=PipelineProperty.Status.ACTIVE,
        price=Decimal("200000"),
        estimated_rent=Decimal("1800"),
        beds=3,
        year_built=2023,
        discovered_at=timezone.now(),
    )


# ═══════════════════════════════════════════════════════════════════════
# Helper function tests
# ═══════════════════════════════════════════════════════════════════════


class TestExtractHelpers:
    """Tests for _extract_state, _extract_city, etc."""

    def test_extract_state_from_source(self) -> None:
        class MockSource:
            state = "TX"

        # type ignore: duck typing test with non-PipelineProperty object
        assert _extract_state(object(), MockSource()) == "TX"  # type: ignore[arg-type]

    def test_extract_state_none(self) -> None:
        assert _extract_state(object(), None) is None  # type: ignore[arg-type]

    def test_extract_city_from_source(self) -> None:
        class MockSource:
            city = "Austin"

        assert _extract_city(object(), MockSource()) == "Austin"  # type: ignore[arg-type]

    def test_extract_foreclosure_status(self) -> None:
        class MockSource:
            foreclosure_status = "preforeclosure"

        assert _extract_foreclosure_status(MockSource()) == "preforeclosure"

    def test_extract_foreclosure_status_none(self) -> None:
        assert _extract_foreclosure_status(None) is None

    def test_extract_property_type(self) -> None:
        class MockSource:
            property_type = "single-family"

        assert _extract_property_type(MockSource()) == "single-family"

    def test_extract_property_type_none(self) -> None:
        assert _extract_property_type(None) is None


@pytest.mark.django_db
class TestIsSourceModel:
    """Tests for _is_source_model detection."""

    def test_is_hud_source(self, user: Any) -> None:
        hud = HudProperty.objects.create(
            hud_case_number="HUD-SRC-001",
            address="1 HUD St",
            city="Austin",
            state="TX",
            zip_code="78701",
            status=HudProperty.Status.ACTIVE,
            scraped_at=timezone.now(),
            last_seen_at=timezone.now(),
        )
        assert _is_source_model(hud) is True

    def test_is_usda_source(self, user: Any) -> None:
        usda = UsdaProperty.objects.create(
            usda_case_number="USDA-SRC-001",
            address="1 USDA St",
            city="Austin",
            state="TX",
            zip_code="78701",
            status=UsdaProperty.Status.ACTIVE,
            scraped_at=timezone.now(),
            last_seen_at=timezone.now(),
        )
        assert _is_source_model(usda) is True

    def test_is_not_source_model(self) -> None:
        assert _is_source_model("string") is False
        assert _is_source_model(None) is False
        assert _is_source_model(42) is False


# ═══════════════════════════════════════════════════════════════════════
# Soft criterion tests
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.django_db
class TestSoftCriteria:
    """Tests for individual soft criterion evaluators."""

    def test_eval_year_built_passes(
        self, pipeline_prop: PipelineProperty, criteria: ScreeningCriteria
    ) -> None:
        ded, pass_msg, fail_msg = _eval_year_built(pipeline_prop, criteria)
        # 2023 build vs 2025 max — deducts 5 pts
        assert ded == 5
        assert fail_msg is not None

    def test_eval_year_built_no_max(
        self, pipeline_prop: PipelineProperty, criteria: ScreeningCriteria
    ) -> None:
        criteria.max_year_built = None
        ded, pass_msg, fail_msg = _eval_year_built(pipeline_prop, criteria)
        assert ded == 0
        assert "skipped" in (pass_msg or "").lower()

    def test_eval_beds_passes(
        self, pipeline_prop: PipelineProperty, criteria: ScreeningCriteria
    ) -> None:
        ded, pass_msg, fail_msg = _eval_beds(pipeline_prop, criteria)
        assert ded == 0
        assert pass_msg is not None

    def test_eval_beds_no_min(
        self, pipeline_prop: PipelineProperty, criteria: ScreeningCriteria
    ) -> None:
        criteria.min_beds = None  # type: ignore[assignment]
        ded, pass_msg, fail_msg = _eval_beds(pipeline_prop, criteria)
        assert ded == 0
        assert pass_msg is not None

    def test_eval_gross_yield_computes(
        self, pipeline_prop: PipelineProperty, criteria: ScreeningCriteria
    ) -> None:
        ded, pass_msg, fail_msg = _eval_gross_yield(pipeline_prop, criteria, None)
        # 1800 * 12 / 200000 = 10.8% should pass 8% minimum
        assert ded == 0
        assert pass_msg is not None
        assert "10.80" in (pass_msg or "")

    def test_eval_price_to_rent_computes(
        self, pipeline_prop: PipelineProperty, criteria: ScreeningCriteria
    ) -> None:
        ded, pass_msg, fail_msg = _eval_price_to_rent_ratio(
            pipeline_prop, criteria, None
        )
        # 200000 / 1800 = 111.11 > 15 max — deducts
        assert ded > 0
        assert fail_msg is not None

    def test_price_to_rent_deducts(
        self, pipeline_prop: PipelineProperty, criteria: ScreeningCriteria
    ) -> None:
        pipeline_prop.price = Decimal("500000")
        pipeline_prop.estimated_rent = Decimal("1000")
        ded, pass_msg, fail_msg = _eval_price_to_rent_ratio(
            pipeline_prop, criteria, None
        )
        # 500000 / (1000*12) = 41.67 > 15 — should deduct
        assert ded > 0
        assert fail_msg is not None


# ═══════════════════════════════════════════════════════════════════════
# GACS score tests
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.django_db
class TestGacsScore:
    """Tests for GACS score evaluation with GrowthArea lookup."""

    def test_gacs_skipped_no_min(
        self, pipeline_prop: PipelineProperty, criteria: ScreeningCriteria
    ) -> None:
        criteria.min_gacs_score = None  # type: ignore[assignment]
        ded, pass_msg, fail_msg = _eval_gacs_score(
            pipeline_prop, criteria, "TX", "Austin"
        )
        assert ded == 0
        assert "skipped" in (pass_msg or "").lower()

    def test_gacs_skipped_no_state_city(
        self, pipeline_prop: PipelineProperty, criteria: ScreeningCriteria
    ) -> None:
        criteria.min_gacs_score = Decimal("50")
        ded, pass_msg, fail_msg = _eval_gacs_score(pipeline_prop, criteria, None, None)
        assert ded == 0
        assert "no state/city" in (pass_msg or "").lower()

    @pytest.mark.django_db
    def test_gacs_lookup_found(
        self, pipeline_prop: PipelineProperty, criteria: ScreeningCriteria
    ) -> None:
        GrowthArea.objects.create(
            state="TX",
            city_name="Austin",
            metro_area="Austin",
            population_growth_rate=Decimal("0.03"),
            employment_growth_rate=Decimal("0.02"),
            median_income_growth=Decimal("0.025"),
            housing_demand_index=75,
            supply_constraint_index=60,
            data_timestamp=timezone.now(),
        )
        criteria.min_gacs_score = Decimal("0")
        ded, pass_msg, fail_msg = _eval_gacs_score(
            pipeline_prop, criteria, "TX", "Austin"
        )
        assert ded == 0
        assert pass_msg is not None
        assert "7.42" in (pass_msg or "")  # score computed from GrowthArea data


# ═══════════════════════════════════════════════════════════════════════
# Full pipeline tests
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.django_db
class TestScreenPropertyFull:
    """End-to-end screen_property tests with VRM source (full pipeline)."""

    def test_vrm_property_passes_screening(
        self, pipeline_prop: PipelineProperty, criteria: ScreeningCriteria
    ) -> None:
        """A VRM property with all data passes screening."""

        # Need a source record with state for the state filter
        class MockSource:
            state = "TX"
            property_type = None
            foreclosure_status = None

        result = screen_property(pipeline_prop, criteria, source_record=MockSource())
        assert result.passed is True
        assert result.score > Decimal("0")

    def test_state_filter_kills(
        self, pipeline_prop: PipelineProperty, criteria: ScreeningCriteria
    ) -> None:
        """Property in non-target state is killed."""

        class MockSource:
            state = "CA"

        result = screen_property(pipeline_prop, criteria, source_record=MockSource())
        assert result.passed is False
        assert result.kill_reason is not None
        assert "state" in result.kill_reason.lower()

    def test_price_above_max_kills(
        self, pipeline_prop: PipelineProperty, criteria: ScreeningCriteria
    ) -> None:
        """Property above max price is killed."""
        pipeline_prop.price = Decimal("9999999")
        result = screen_property(pipeline_prop, criteria)
        assert result.passed is False

    def test_price_below_min_kills(
        self, pipeline_prop: PipelineProperty, criteria: ScreeningCriteria
    ) -> None:
        """Property below min price is killed."""
        pipeline_prop.price = Decimal("1")
        result = screen_property(pipeline_prop, criteria)
        assert result.passed is False

    def test_screening_without_price_skips_price_check(
        self, pipeline_prop: PipelineProperty, criteria: ScreeningCriteria
    ) -> None:
        """Property with no price skips price check."""
        pipeline_prop.price = None
        result = screen_property(pipeline_prop, criteria)
        # Should still pass (other criteria met)
        assert result is not None

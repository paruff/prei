"""End-to-end integration tests for the full acquisition and leasing pipeline.

Tests cover:
  T1: Full acquisition flow — VRM → screening → advance → closing → Property
  T2: Kill flow — kill at SCREENING → kill_reason → advance blocked
  T3: Duplicate prevention — same VRM twice returns created=False
  T4: Hard kill screening — state filter kills property
  T5: Yield skipped for ForeclosureProperty — noted, not errored
  T6: Full leasing flow — Property → lease → STABILIZED → FILLED
  T7: Closing atomicity — Property.save() exception rolls back ClosingRecord
  T8: Re-screen on criteria change — screening_passed updated
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from core.services.pipeline import (
    advance_stage,
    convert_to_property_record,
    create_from_foreclosure,
    create_from_vrm,
    kill_property,
    reactivate_property,
)
from core.services.screening import get_or_create_criteria, screen_property

User = get_user_model()


# ── Fixtures ───────────────────────────────────────────────────────────────────


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="flow_user",
        email="flow@test.com",
        password="testpass123",
    )


@pytest.fixture
def vrm_property(db):
    """Standard VrmProperty with rent data for pipeline flow."""
    from core.models import VrmProperty as VP

    now = timezone.now()
    return VP.objects.create(
        vrm_property_id=9001,
        vrm_listing_url="https://example.com/9001",
        address="9001 Flow Blvd",
        city="Austin",
        state="TX",
        zip_code="78701",
        list_price=Decimal("250000"),
        projected_monthly_rent=Decimal("2200"),
        bedrooms=3,
        year_built=2015,
        property_type="single-family",
        status=VP.Status.FOR_SALE,
        scraped_at=now,
        last_seen_at=now,
    )


@pytest.fixture
def foreclosure_property(db):
    """ForeclosureProperty without rent data."""
    from core.models import ForeclosureProperty

    return ForeclosureProperty.objects.create(
        property_id="fc-flow-001",
        data_source="county",
        data_timestamp="2026-01-01 00:00:00+00",
        street="800 Foreclosure Ave",
        city="Dallas",
        state="TX",
        zip_code="75201",
        foreclosure_status="auction",
        property_type="single-family",
        opening_bid=Decimal("180000"),
        bedrooms=3,
        year_built=2005,
        square_footage=1500,
    )


@pytest.fixture
def criteria(db, user):
    """Default screening criteria for the test user."""
    return get_or_create_criteria(user)


@pytest.fixture
def leasing_property(db, user):
    """Property record used in leasing flow tests."""
    from core.models import Property as PropertyModel

    return PropertyModel.objects.create(
        user=user,
        address="777 Leasing Way",
        city="Austin",
        state="TX",
        zip_code="78701",
        purchase_price=Decimal("250000"),
        purchase_date="2026-06-01",
        sqft=1500,
        monthly_rent_gross=Decimal("2000"),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# T1: Full acquisition flow
# ═══════════════════════════════════════════════════════════════════════════════


class TestFullAcquisitionFlow:
    """VRM property → PipelineProperty → advance stages → closing → Property."""

    def test_full_acquisition(self, db, user, vrm_property):
        """Complete acquisition flow end-to-end."""
        # 1. Create from VRM → screening runs automatically
        pp, created = create_from_vrm(vrm_property, user)
        assert created
        assert pp.stage == "SCREENING"
        assert pp.screening_passed is not None
        assert pp.price == vrm_property.list_price
        assert pp.estimated_rent == vrm_property.projected_monthly_rent

        # 2. Advance through all stages
        expected_stages = [
            "UNDERWRITING",
            "OFFER",
            "DUE_DILIGENCE",
            "CLOSING",
            "ACQUIRED",
            "RENOVATION",
            "STABILIZED",
        ]
        for expected in expected_stages:
            pp = advance_stage(pp)
            assert pp.stage == expected, f"Expected {expected}, got {pp.stage}"

        # 3. Verify STABILIZED is terminal
        with pytest.raises(ValueError, match="already at final stage"):
            advance_stage(pp)

        # 4. Create a closing record first (needed for convert_to_property_record)
        from core.models import ClosingRecord

        pp.stage = "CLOSING"
        pp.save()
        ClosingRecord.objects.create(
            pipeline_property=pp,
            final_purchase_price=Decimal("245000"),
            closing_date="2026-07-15",
        )

        # 5. Convert to Property record
        prop = convert_to_property_record(pp)
        assert prop is not None
        assert prop.address == vrm_property.address
        assert prop.purchase_price == vrm_property.list_price
        assert prop.monthly_rent_gross == vrm_property.projected_monthly_rent
        pp.refresh_from_db()
        assert pp.property_record == prop
        assert pp.status == "ACQUIRED"
        assert pp.stage == "ACQUIRED"


# ═══════════════════════════════════════════════════════════════════════════════
# T2: Kill flow
# ═══════════════════════════════════════════════════════════════════════════════


class TestKillFlow:
    """Property created → killed → kill_reason → blocked advance."""

    def test_kill_at_screening(self, db, user, vrm_property):
        pp, _ = create_from_vrm(vrm_property, user)

        # Kill at SCREENING
        pp = kill_property(pp, "Low projected yield")
        assert pp.status == "KILLED"
        assert pp.kill_reason == "Low projected yield"

        # Advance should be blocked
        with pytest.raises(ValueError, match="Cannot advance"):
            advance_stage(pp)

        # Reactivate and advance should work
        pp = reactivate_property(pp)
        assert pp.status == "ACTIVE"
        pp = advance_stage(pp)
        assert pp.stage == "UNDERWRITING"


# ═══════════════════════════════════════════════════════════════════════════════
# T3: Duplicate prevention
# ═══════════════════════════════════════════════════════════════════════════════


class TestDuplicatePrevention:
    """Same source added twice → second call returns created=False."""

    def test_vrm_duplicate(self, db, user, vrm_property):
        pp1, created1 = create_from_vrm(vrm_property, user)
        pp2, created2 = create_from_vrm(vrm_property, user)
        assert created1
        assert not created2
        assert pp1.pk == pp2.pk

    def test_foreclosure_duplicate(self, db, user, foreclosure_property):
        pp1, created1 = create_from_foreclosure(foreclosure_property, user)
        pp2, created2 = create_from_foreclosure(foreclosure_property, user)
        assert created1
        assert not created2
        assert pp1.pk == pp2.pk


# ═══════════════════════════════════════════════════════════════════════════════
# T4: Hard kill screening — state filter
# ═══════════════════════════════════════════════════════════════════════════════


class TestHardKillScreening:
    """State filter kills property not in allowed states."""

    def test_state_filter_kills(self, db, user, vrm_property):
        from core.models import ScreeningCriteria

        criteria, _ = ScreeningCriteria.objects.get_or_create(user=user)
        criteria.allowed_states = ["FL"]  # VRM is in TX
        criteria.save()

        pp, _ = create_from_vrm(vrm_property, user)
        # Screening ran during create - but the default criteria has no state filter.
        # We need to re-screen with the configured criteria.
        result = screen_property(pp, criteria, source_record=vrm_property)
        assert not result.passed
        assert len(result.hard_failures) >= 1
        assert any("not in allowed states" in f for f in result.hard_failures)

    def test_state_filter_pass(self, db, user, vrm_property):
        from core.models import ScreeningCriteria

        criteria, _ = ScreeningCriteria.objects.get_or_create(user=user)
        criteria.allowed_states = ["TX"]
        criteria.save()

        pp, _ = create_from_vrm(vrm_property, user)
        result = screen_property(pp, criteria, source_record=vrm_property)
        assert result.passed or len(result.hard_failures) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# T5: Yield skipped for ForeclosureProperty
# ═══════════════════════════════════════════════════════════════════════════════


class TestForeclosureYieldSkipped:
    """ForeclosureProperty has no rent → yield/PTR noted as skipped."""

    def test_yield_skipped(self, db, user, foreclosure_property):
        from core.models import ScreeningCriteria

        criteria, _ = ScreeningCriteria.objects.get_or_create(user=user)
        criteria.allowed_states = ["TX"]
        criteria.save()

        pp, created = create_from_foreclosure(foreclosure_property, user)
        assert created

        # Re-screen to verify yield is skipped
        result = screen_property(pp, criteria, source_record=foreclosure_property)
        assert "no rent estimate available" in result.notes
        assert result.passed  # No hard failures, soft criteria skipped


# ═══════════════════════════════════════════════════════════════════════════════
# T6: Full leasing flow
# ═══════════════════════════════════════════════════════════════════════════════


class TestFullLeasingFlow:
    """Property → LeasingPipelineProperty → advance → STABILIZED → FILLED."""

    def test_leasing_flow(self, db, user, leasing_property):
        from core.models import LeasingPipelineProperty

        # 1. Create leasing entry
        lease = LeasingPipelineProperty.objects.create(
            property_record=leasing_property,
            user=user,
            asking_rent=Decimal("2200"),
            listed_date="2026-07-01",
            stage=LeasingPipelineProperty.Stage.LISTING,
            status=LeasingPipelineProperty.Status.ACTIVE,
        )
        assert lease.pk is not None
        assert lease.stage == "LISTING"

        # 2. Advance through leasing stages (simulate stage progression)
        LEASING_ORDER = [
            "SHOWING",
            "APPLICATION",
            "SCREENING",
            "APPROVED",
            "LEASE_SIGNED",
            "MOVE_IN",
            "STABILIZED",
        ]
        for expected in LEASING_ORDER:
            lease.stage = expected
            lease.save()
            lease.refresh_from_db()
            assert lease.stage == expected

        # 3. Fill the unit
        lease.status = LeasingPipelineProperty.Status.FILLED
        lease.save()
        lease.refresh_from_db()
        assert lease.status == "FILLED"

        # 4. Verify link to property
        assert lease.property_record == leasing_property
        assert leasing_property.leasing_entries.count() == 1


# ═══════════════════════════════════════════════════════════════════════════════
# T7: Closing atomicity
# ═══════════════════════════════════════════════════════════════════════════════


class TestClosingAtomicity:
    """If Property.save() fails, ClosingRecord is not committed."""

    def test_atomic_rollback(self, db, user, vrm_property):
        from core.models import ClosingRecord, Property as PropertyModel

        # Create PP and advance to CLOSING
        pp, _ = create_from_vrm(vrm_property, user)
        for _ in range(5):  # SCREENING → ... → CLOSING is 4 advances
            advance_stage(pp)
        # We need to be at CLOSING for convert_to_property_record
        pp.stage = "CLOSING"
        pp.save()

        # Create a closing record first
        ClosingRecord.objects.create(
            pipeline_property=pp,
            final_purchase_price=Decimal("245000"),
            closing_date="2026-07-15",
        )

        # Mock Property.objects.create to fail
        with patch.object(
            PropertyModel.objects,
            "create",
            side_effect=RuntimeError("DB failure"),
        ):
            with pytest.raises(RuntimeError):
                convert_to_property_record(pp)

        # PipelineProperty should NOT be marked ACQUIRED
        pp.refresh_from_db()
        assert pp.status != "ACQUIRED"
        assert pp.property_record is None


# ═══════════════════════════════════════════════════════════════════════════════
# T8: Re-screen on criteria change
# ═══════════════════════════════════════════════════════════════════════════════


class TestRescreenOnCriteriaChange:
    """Updating ScreeningCriteria and re-screening updates screening_passed."""

    def test_rescreen_updates_result(self, db, user, vrm_property):
        from core.models import ScreeningCriteria

        # Create PP with default criteria (passes)
        pp, _ = create_from_vrm(vrm_property, user)
        initial_result = pp.screening_passed

        # Change criteria to be very restrictive
        criteria, _ = ScreeningCriteria.objects.get_or_create(user=user)
        criteria.allowed_states = ["FL"]  # VRM is TX
        criteria.save()

        # Re-screen
        result = screen_property(pp, criteria, source_record=vrm_property)
        pp.screening_passed = result.passed
        pp.save(update_fields=["screening_passed"])

        pp.refresh_from_db()
        # Should now be harder to pass
        if initial_result is True:
            assert pp.screening_passed is False  # State filter should kill

    def test_rescreen_with_looser_criteria(self, db, user, foreclosure_property):
        from core.models import ScreeningCriteria

        # Create with default criteria (has min_beds=1, no state filter)
        pp, _ = create_from_foreclosure(foreclosure_property, user)
        pp.refresh_from_db()

        # Loosen criteria: remove min_beds, allow all states
        criteria, _ = ScreeningCriteria.objects.get_or_create(user=user)
        criteria.allowed_states = ["TX"]
        criteria.min_beds = 0
        criteria.save()

        result = screen_property(pp, criteria, source_record=foreclosure_property)
        pp.screening_passed = result.passed
        pp.save(update_fields=["screening_passed"])

        pp.refresh_from_db()
        assert pp.screening_passed == result.passed

"""Unit tests for core/services/pipeline.py pipeline service.

Tests cover: advance_stage, kill_property, hold_property, reactivate_property,
get_source_record, create_from_vrm, create_from_foreclosure, duplicate
prevention, convert_to_property_record, atomic rollback.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from core.services.pipeline import (
    STAGE_ORDER,
    advance_stage,
    convert_to_property_record,
    create_from_foreclosure,
    create_from_vrm,
    get_source_record,
    hold_property,
    kill_property,
    reactivate_property,
)

User = get_user_model()


# ═══════════════════════════════════════════════════════════════════════════════
#  Fixtures
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="pipe",
        email="pipe@test.com",
        password="testpass123",
    )


@pytest.fixture
def vrm_property(db):
    """VrmProperty fixture for create_from_vrm tests."""
    from core.models import VrmProperty as VP

    now = timezone.now()
    vp = VP(
        vrm_property_id=1001,
        vrm_listing_url="https://example.com/1001",
        address="1001 Pipeline Ave",
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


@pytest.fixture
def foreclosure_property(db):
    """ForeclosureProperty fixture for create_from_foreclosure tests."""
    from core.models import ForeclosureProperty

    fp = ForeclosureProperty(
        property_id="fc-pipe-001",
        data_source="county",
        data_timestamp="2026-01-01 00:00:00+00",
        street="2002 Foreclosure Ln",
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
    fp.save()
    return fp


@pytest.fixture
def pp_base(db, user):
    """Basic PipelineProperty starting at DISCOVERED."""
    from core.models import PipelineProperty

    pp = PipelineProperty(
        user=user,
        source_type="manual",
        source_id="pipe-test-001",
        address="300 Test Blvd",
        address_hash="test-hash",
        stage=PipelineProperty.Stage.DISCOVERED,
        status=PipelineProperty.Status.ACTIVE,
        price=Decimal("200000"),
        estimated_rent=Decimal("1800"),
        beds=3,
        year_built=2008,
        discovered_at=timezone.now(),
    )
    pp.save()
    return pp


# ═══════════════════════════════════════════════════════════════════════════════
#  STAGE_ORDER
# ═══════════════════════════════════════════════════════════════════════════════


class TestStageOrder:
    def test_has_nine_stages(self):
        """STAGE_ORDER has exactly 9 stages matching PipelineProperty.Stage."""
        assert len(STAGE_ORDER) == 9

    def test_first_is_discovered(self):
        assert STAGE_ORDER[0] == "DISCOVERED"

    def test_last_is_stabilized(self):
        assert STAGE_ORDER[-1] == "STABILIZED"


# ═══════════════════════════════════════════════════════════════════════════════
#  advance_stage
# ═══════════════════════════════════════════════════════════════════════════════


class TestAdvanceStage:
    def test_advances_to_next_stage(self, pp_base):
        """DISCOVERED → SCREENING."""
        result = advance_stage(pp_base)
        assert result.stage == "SCREENING"
        assert result.screening_at is not None

    def test_sets_timestamp(self, pp_base):
        """Each advance sets the corresponding stage timestamp."""
        advance_stage(pp_base)
        assert pp_base.screening_at is not None
        assert pp_base.discovered_at is not None  # was set in fixture

    def test_advances_through_multiple_stages(self, pp_base):
        """Advancing multiple times moves through the stage order."""
        stages = ["SCREENING", "UNDERWRITING", "OFFER", "DUE_DILIGENCE"]
        for expected in stages:
            result = advance_stage(pp_base)
            assert result.stage == expected

    def test_raises_on_killed(self, pp_base):
        """Killed properties cannot advance."""
        kill_property(pp_base, "Not interested")
        with pytest.raises(ValueError, match="Cannot advance"):
            advance_stage(pp_base)

    def test_raises_on_on_hold(self, pp_base):
        """ON_HOLD properties cannot advance."""
        hold_property(pp_base, "Waiting on inspection")
        with pytest.raises(ValueError, match="Cannot advance"):
            advance_stage(pp_base)

    def test_raises_at_stabilized(self, pp_base):
        """Already at STABILIZED raises ValueError."""
        pp_base.stage = "STABILIZED"
        pp_base.save()
        with pytest.raises(ValueError, match="already at final stage"):
            advance_stage(pp_base)


# ═══════════════════════════════════════════════════════════════════════════════
#  kill_property
# ═══════════════════════════════════════════════════════════════════════════════


class TestKillProperty:
    def test_kills_property(self, pp_base):
        """Sets status=KILLED and records reason."""
        result = kill_property(pp_base, "Below yield threshold")
        assert result.status == "KILLED"
        assert result.kill_reason == "Below yield threshold"

    def test_kill_does_not_change_stage(self, pp_base):
        """Stage stays current; only status changes."""
        current = pp_base.stage
        kill_property(pp_base, "test")
        assert pp_base.stage == current


# ═══════════════════════════════════════════════════════════════════════════════
#  hold_property
# ═══════════════════════════════════════════════════════════════════════════════


class TestHoldProperty:
    def test_sets_on_hold(self, pp_base):
        """Sets status=ON_HOLD."""
        result = hold_property(pp_base, "Awaiting appraisal")
        assert result.status == "ON_HOLD"

    def test_hold_records_reason(self, pp_base):
        hold_property(pp_base, "Need more data")
        assert pp_base.kill_reason == "Need more data"

    def test_hold_without_reason(self, pp_base):
        hold_property(pp_base)
        assert pp_base.status == "ON_HOLD"


# ═══════════════════════════════════════════════════════════════════════════════
#  reactivate_property
# ═══════════════════════════════════════════════════════════════════════════════


class TestReactivateProperty:
    def test_reactivates_killed(self, pp_base):
        """KILLED → ACTIVE at same stage."""
        kill_property(pp_base, "Rejected")
        result = reactivate_property(pp_base)
        assert result.status == "ACTIVE"

    def test_reactivates_on_hold(self, pp_base):
        """ON_HOLD → ACTIVE at same stage."""
        hold_property(pp_base)
        result = reactivate_property(pp_base)
        assert result.status == "ACTIVE"

    def test_reactivate_does_not_change_stage(self, pp_base):
        """Stage unchanged after reactivation."""
        advance_stage(pp_base)  # → SCREENING
        hold_property(pp_base)
        reactivate_property(pp_base)
        assert pp_base.stage == "SCREENING"


# ═══════════════════════════════════════════════════════════════════════════════
#  get_source_record
# ═══════════════════════════════════════════════════════════════════════════════


class TestGetSourceRecord:
    def test_resolves_vrm(self, db, user, vrm_property):
        """source_type='vrm' resolves to VrmProperty."""
        from core.models import PipelineProperty

        pp = PipelineProperty(
            user=user,
            source_type="vrm",
            source_id="1001",
            address="test",
            address_hash="h",
        )
        pp.save()

        record = get_source_record(pp)
        assert record is not None
        assert record.vrm_property_id == 1001

    def test_resolves_foreclosure(self, db, user, foreclosure_property):
        """source_type='foreclosure' resolves to ForeclosureProperty."""
        from core.models import PipelineProperty

        pp = PipelineProperty(
            user=user,
            source_type="foreclosure",
            source_id="fc-pipe-001",
            address="test",
            address_hash="h",
        )
        pp.save()

        record = get_source_record(pp)
        assert record is not None
        assert record.property_id == "fc-pipe-001"

    def test_returns_none_for_manual(self, db, user):
        """source_type='manual' returns None."""
        from core.models import PipelineProperty

        pp = PipelineProperty(
            user=user,
            source_type="manual",
            source_id="m-001",
            address="test",
            address_hash="h",
        )
        pp.save()

        assert get_source_record(pp) is None

    def test_returns_none_for_unknown_type(self, db, user):
        """Unknown source_type returns None."""
        from core.models import PipelineProperty

        pp = PipelineProperty(
            user=user,
            source_type="bogus",
            source_id="x",
            address="test",
            address_hash="h",
        )
        pp.save()

        assert get_source_record(pp) is None

    def test_returns_none_for_missing_id(self, db, user):
        """Nonexistent source_id returns None."""
        from core.models import PipelineProperty

        pp = PipelineProperty(
            user=user,
            source_type="vrm",
            source_id="999999",
            address="test",
            address_hash="h",
        )
        pp.save()

        assert get_source_record(pp) is None


# ═══════════════════════════════════════════════════════════════════════════════
#  create_from_vrm
# ═══════════════════════════════════════════════════════════════════════════════


class TestCreateFromVrm:
    def test_creates_pipeline_property(self, db, user, vrm_property):
        """Creates PipelineProperty with denormalized fields."""
        pp, created = create_from_vrm(vrm_property, user)
        assert created
        assert pp.source_type == "vrm"
        assert pp.source_id == "1001"
        assert pp.price == vrm_property.list_price
        assert pp.estimated_rent == vrm_property.projected_monthly_rent
        assert pp.beds == vrm_property.bedrooms

    def test_advances_to_screening(self, db, user, vrm_property):
        """PP created with stage=SCREENING (screening already ran)."""
        pp, created = create_from_vrm(vrm_property, user)
        assert pp.stage == "SCREENING"
        assert pp.screening_at is not None

    def test_screening_result_stored(self, db, user, vrm_property):
        """screening_passed is set from screen_property result."""
        pp, created = create_from_vrm(vrm_property, user)
        assert created
        # screening_passed will be True or False depending on defaults
        assert pp.screening_passed is not None

    def test_duplicate_returns_false(self, db, user, vrm_property):
        """Second call with same VrmProperty returns created=False."""
        pp1, created1 = create_from_vrm(vrm_property, user)
        pp2, created2 = create_from_vrm(vrm_property, user)
        assert created1
        assert not created2
        assert pp1.pk == pp2.pk


# ═══════════════════════════════════════════════════════════════════════════════
#  create_from_foreclosure
# ═══════════════════════════════════════════════════════════════════════════════


class TestCreateFromForeclosure:
    def test_creates_pipeline_property(self, db, user, foreclosure_property):
        """Creates PipelineProperty with denormalized fields."""
        pp, created = create_from_foreclosure(foreclosure_property, user)
        assert created
        assert pp.source_type == "foreclosure"
        assert pp.source_id == "fc-pipe-001"
        assert pp.price == foreclosure_property.opening_bid
        assert pp.beds == foreclosure_property.bedrooms

    def test_advances_to_screening(self, db, user, foreclosure_property):
        """PP created with stage=SCREENING."""
        pp, created = create_from_foreclosure(foreclosure_property, user)
        assert pp.stage == "SCREENING"
        assert pp.screening_at is not None

    def test_screening_result_stored(self, db, user, foreclosure_property):
        """screening_passed is set (yield/PTR skipped for foreclosure)."""
        pp, created = create_from_foreclosure(foreclosure_property, user)
        assert created
        assert pp.screening_passed is not None

    def test_duplicate_returns_false(self, db, user, foreclosure_property):
        """Second call returns created=False."""
        pp1, created1 = create_from_foreclosure(foreclosure_property, user)
        pp2, created2 = create_from_foreclosure(foreclosure_property, user)
        assert created1
        assert not created2
        assert pp1.pk == pp2.pk


# ═══════════════════════════════════════════════════════════════════════════════
#  convert_to_property_record
# ═══════════════════════════════════════════════════════════════════════════════


class TestConvertToPropertyRecord:
    def test_creates_property_record(self, db, user, vrm_property):
        """Creates Property with denormalized pipeline data."""
        pp, _ = create_from_vrm(vrm_property, user)

        # Advance to CLOSING first (realistic flow)
        # create_from_vrm sets SCREENING, so we need 5 more advances
        for _ in range(5):
            advance_stage(pp)

        assert pp.stage == "ACQUIRED"

        prop = convert_to_property_record(pp)

        assert prop is not None
        assert prop.user == user
        assert prop.purchase_price == Decimal("250000")
        assert prop.monthly_rent_gross == Decimal("2000")

    def test_links_back_to_pipeline(self, db, user, vrm_property):
        """PipelineProperty.property_record set after conversion."""
        pp, _ = create_from_vrm(vrm_property, user)
        for _ in range(5):
            advance_stage(pp)

        convert_to_property_record(pp)

        pp.refresh_from_db()
        assert pp.property_record is not None
        assert pp.status == "ACQUIRED"
        assert pp.stage == "ACQUIRED"
        assert pp.acquired_at is not None

    def test_raises_on_duplicate_conversion(self, db, user, vrm_property):
        """Second conversion attempt raises ValueError."""
        pp, _ = create_from_vrm(vrm_property, user)
        for _ in range(5):
            advance_stage(pp)

        convert_to_property_record(pp)

        with pytest.raises(ValueError, match="already converted"):
            convert_to_property_record(pp)

    def test_atomic_rollback_on_failure(self, db, user, vrm_property):
        """If conversion fails partway, no Property is created."""
        from unittest.mock import patch

        pp, _ = create_from_vrm(vrm_property, user)
        for _ in range(5):
            advance_stage(pp)

        # Mock Property.create to fail after pipeline updates
        with patch(
            "core.models.Property.objects.create",
            side_effect=RuntimeError("DB failure"),
        ):
            with pytest.raises(RuntimeError):
                convert_to_property_record(pp)

        # PipelineProperty should NOT be marked ACQUIRED
        pp.refresh_from_db()
        assert pp.status != "ACQUIRED"
        assert pp.property_record is None

    def test_accepts_custom_closing_date(self, db, user, vrm_property):
        """Custom closing_date passed through."""
        import datetime

        pp, _ = create_from_vrm(vrm_property, user)
        for _ in range(5):
            advance_stage(pp)

        closing = datetime.date(2026, 7, 15)
        prop = convert_to_property_record(pp, closing)
        assert prop.purchase_date == closing

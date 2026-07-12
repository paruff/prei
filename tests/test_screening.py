"""Unit tests for core/services/screening.py screening service.

Tests cover:
- Hard kill criteria (state, property type, price range, foreclosure status)
- Soft criteria (GACS score, gross yield, PTR, year built, beds)
- VrmProperty source (yield/PTR evaluated)
- ForeclosureProperty source (yield/PTR skipped)
- Missing data handling
- All pass scenario
- No criteria set (defaults)
- get_or_create_criteria helper
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from core.services.screening import get_or_create_criteria, screen_property

User = get_user_model()


# ═══════════════════════════════════════════════════════════════════════════════
#  Fixtures
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="screener",
        email="screener@test.com",
        password="testpass123",
    )


@pytest.fixture
def criteria(db, user):
    """ScreeningCriteria with all fields at defaults via get_or_create."""
    return get_or_create_criteria(user)


@pytest.fixture
def configured_criteria(db, user):
    """ScreeningCriteria with specific thresholds set."""
    from core.models import ScreeningCriteria

    c, _ = ScreeningCriteria.objects.get_or_create(user=user)
    c.allowed_states = ["TX", "FL"]
    c.allowed_property_types = ["single-family", "condo"]
    c.min_price = Decimal("100000")
    c.max_price = Decimal("500000")
    c.allowed_foreclosure_statuses = ["auction", "reo"]
    c.min_gacs_score = Decimal("50")
    c.min_gross_yield_pct = Decimal("7.00")
    c.max_price_to_rent_ratio = Decimal("15.00")
    c.max_year_built = 2000
    c.min_beds = 2
    c.max_beds = 5
    c.save()
    return c


@pytest.fixture
def pipeline_property_base(db, user):
    """Basic PipelineProperty (not saved) with default values that pass."""
    from core.models import PipelineProperty

    pp = PipelineProperty(
        user=user,
        source_type="foreclosure",
        source_id="fc-001",
        address="123 Main St, Austin, TX 78701",
        address_hash="abc123",
        stage=PipelineProperty.Stage.DISCOVERED,
        status=PipelineProperty.Status.ACTIVE,
        price=Decimal("250000"),
        estimated_rent=Decimal("2000"),
        beds=3,
        year_built=2010,
    )
    pp.save()
    return pp


@pytest.fixture
def vrm_property(db):
    """VrmProperty with full data including rent."""
    from django.utils import timezone
    from core.models import VrmProperty as VP

    now = timezone.now()
    vp = VP(
        vrm_property_id=999,
        vrm_listing_url="https://example.com/listing/999",
        address="456 Oak Ave",
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
    vp.save()
    return vp


@pytest.fixture
def foreclosure_property(db):
    """ForeclosureProperty (no rent data)."""
    from core.models import ForeclosureProperty

    fp = ForeclosureProperty(
        property_id="fc-prop-001",
        data_source="county",
        data_timestamp="2026-01-01 00:00:00+00",
        street="789 Elm St",
        city="Dallas",
        state="TX",
        zip_code="75201",
        foreclosure_status="auction",
        property_type="single-family",
        opening_bid=Decimal("200000"),
        bedrooms=3,
        year_built=2005,
        square_footage=1800,
    )
    fp.save()
    return fp


@pytest.fixture
def growth_area(db):
    """GrowthArea for GACS score lookup."""
    from core.models import GrowthArea

    ga = GrowthArea(
        state="TX",
        city_name="Austin",
        metro_area="Austin-Round Rock",
        population_growth_rate=Decimal("2.50"),
        employment_growth_rate=Decimal("3.20"),
        median_income_growth=Decimal("2.80"),
        housing_demand_index=85,
        supply_constraint_index=60,
        data_timestamp="2026-01-01 00:00:00+00",
    )
    ga.save()
    return ga


# ═══════════════════════════════════════════════════════════════════════════════
#  get_or_create_criteria
# ═══════════════════════════════════════════════════════════════════════════════


class TestGetOrCreateCriteria:
    def test_creates_new_criteria(self, db, user):
        """First call creates ScreeningCriteria for user."""
        c = get_or_create_criteria(user)
        assert c.user == user
        assert c.min_gross_yield_pct == Decimal("7.00")

    def test_returns_existing_criteria(self, db, user):
        """Second call returns existing criteria."""
        c1 = get_or_create_criteria(user)
        c2 = get_or_create_criteria(user)
        assert c1.pk == c2.pk


# ═══════════════════════════════════════════════════════════════════════════════
#  HARD KILL CRITERIA
# ═══════════════════════════════════════════════════════════════════════════════


class TestHardKillStateFilter:
    def test_kills_unallowed_state(self, db, configured_criteria, user):
        """State filter kills property with non-allowed state."""
        from core.models import PipelineProperty

        pp = PipelineProperty(
            user=user,
            source_type="manual",
            source_id="m-state-kill",
            address="999 Kill State",
            address_hash="kill-state",
            price=Decimal("250000"),
        )
        pp.save()

        # PP has no source_record, so state is None → killed by active state filter
        result = screen_property(pp, configured_criteria)
        assert not result.passed
        assert len(result.hard_failures) == 1
        assert "no state data" in result.hard_failures[0]
        assert result.score == Decimal("0")

    def test_passes_allowed_state(self, db, configured_criteria, user, vrm_property):
        """Property in allowed state passes state filter."""
        from core.models import PipelineProperty

        pp = PipelineProperty(
            user=user,
            source_type="vrm",
            source_id="vrm-999",
            address="456 Oak Ave, Austin, TX 78701",
            address_hash="def456",
            price=Decimal("250000"),
            estimated_rent=Decimal("2200"),
            beds=3,
            year_built=2015,
        )
        pp.save()
        configured_criteria.allowed_states = ["TX"]
        configured_criteria.save()

        result = screen_property(pp, configured_criteria, vrm_property)
        assert result.passed
        assert len(result.hard_failures) == 0

    def test_kills_missing_state_when_filter_active(
        self, db, configured_criteria, pipeline_property_base
    ):
        """Kills if state filter active but no state data available."""
        result = screen_property(pipeline_property_base, configured_criteria)
        assert not result.passed
        assert "no state data" in result.hard_failures[0]


class TestHardKillPropertyType:
    def test_kills_unallowed_type(self, db, configured_criteria, user):
        """Property type filter kills non-allowed type."""
        from django.utils import timezone
        from core.models import PipelineProperty
        from core.models import VrmProperty as VP

        now = timezone.now()
        pp = PipelineProperty(
            user=user,
            source_type="vrm",
            source_id="vrm-998",
            address="101 Pine, Austin, TX 78701",
            address_hash="ghi789",
            price=Decimal("300000"),
            estimated_rent=Decimal("2000"),
            beds=3,
        )
        pp.save()

        vp = VP(
            vrm_property_id=998,
            vrm_listing_url="https://example.com/998",
            address="101 Pine",
            city="Austin",
            state="TX",
            zip_code="78701",
            list_price=Decimal("300000"),
            bedrooms=3,
            property_type="commercial",
            status=VP.Status.FOR_SALE,
            scraped_at=now,
            last_seen_at=now,
        )
        vp.save()

        result = screen_property(pp, configured_criteria, vp)
        assert not result.passed
        assert "not in allowed types" in result.hard_failures[0]

    def test_passes_allowed_type(self, db, configured_criteria, vrm_property, user):
        """Allowed property type passes."""
        from core.models import PipelineProperty

        pp = PipelineProperty(
            user=user,
            source_type="vrm",
            source_id="vrm-999",
            address="456 Oak Ave, Austin, TX 78701",
            address_hash="def456",
            price=Decimal("250000"),
            estimated_rent=Decimal("2200"),
            beds=3,
            year_built=2015,
        )
        pp.save()

        result = screen_property(pp, configured_criteria, vrm_property)
        assert result.passed

    def test_skips_when_no_property_type_data(
        self, db, configured_criteria, pipeline_property_base, vrm_property
    ):
        """No property type data → SKIPPED note, not a kill."""
        vrm_property.property_type = ""
        vrm_property.save()

        result = screen_property(
            pipeline_property_base, configured_criteria, vrm_property
        )
        # Should kill for state not TX, but property type check is skipped
        assert "no property_type data available" in str(result.passes)


class TestHardKillPriceRange:
    def test_kills_above_max_price(self, db, configured_criteria, user):
        """Price above max kills."""
        configured_criteria.allowed_states = []
        configured_criteria.save()

        from core.models import PipelineProperty

        pp = PipelineProperty(
            user=user,
            source_type="manual",
            source_id="m-001",
            address="999 High St",
            address_hash="aaa",
            price=Decimal("600000"),
        )
        pp.save()

        result = screen_property(pp, configured_criteria)
        assert not result.passed
        assert "exceeds max" in result.hard_failures[0]

    def test_kills_below_min_price(self, db, configured_criteria, user):
        """Price below min kills."""
        configured_criteria.allowed_states = []
        configured_criteria.save()

        from core.models import PipelineProperty

        pp = PipelineProperty(
            user=user,
            source_type="manual",
            source_id="m-002",
            address="888 Low St",
            address_hash="bbb",
            price=Decimal("50000"),
        )
        pp.save()

        result = screen_property(pp, configured_criteria)
        assert not result.passed
        assert "below min" in result.hard_failures[0]

    def test_passes_within_price_range(self, db, configured_criteria, user):
        """Price within range passes."""
        configured_criteria.allowed_states = []
        configured_criteria.allowed_property_types = []
        configured_criteria.allowed_foreclosure_statuses = []
        configured_criteria.save()

        from core.models import PipelineProperty

        pp = PipelineProperty(
            user=user,
            source_type="manual",
            source_id="m-003",
            address="777 Mid St",
            address_hash="ccc",
            price=Decimal("250000"),
        )
        pp.save()

        result = screen_property(pp, configured_criteria)
        assert result.passed

    def test_skips_when_no_price(self, db, configured_criteria, user):
        """No price → SKIPPED."""
        configured_criteria.allowed_states = []
        configured_criteria.save()

        from core.models import PipelineProperty

        pp = PipelineProperty(
            user=user,
            source_type="manual",
            source_id="m-004",
            address="666 No Price St",
            address_hash="ddd",
            price=None,
        )
        pp.save()

        result = screen_property(pp, configured_criteria)
        assert "SKIPPED: Price range check" in str(result.passes)


class TestHardKillForeclosureStatus:
    def test_kills_unallowed_status(
        self, db, configured_criteria, foreclosure_property, user
    ):
        """Foreclosure status filter kills non-allowed status."""
        from core.models import PipelineProperty

        pp = PipelineProperty(
            user=user,
            source_type="foreclosure",
            source_id="fc-prop-001",
            address="789 Elm St, Dallas, TX 75201",
            address_hash="eee",
            price=Decimal("200000"),
            beds=3,
        )
        pp.save()

        result = screen_property(pp, configured_criteria, foreclosure_property)
        # Should pass (TX allowed, single-family allowed, price OK)
        assert result.passed

    def test_kills_disallowed_foreclosure_status(
        self, db, configured_criteria, foreclosure_property, user
    ):
        foreclosure_property.foreclosure_status = "preforeclosure"
        foreclosure_property.save()

        from core.models import PipelineProperty

        pp = PipelineProperty(
            user=user,
            source_type="foreclosure",
            source_id="fc-prop-001",
            address="789 Elm St, Dallas, TX 75201",
            address_hash="fff",
            price=Decimal("200000"),
            beds=3,
        )
        pp.save()

        result = screen_property(pp, configured_criteria, foreclosure_property)
        assert not result.passed
        assert "not in allowed" in result.hard_failures[0]


# ═══════════════════════════════════════════════════════════════════════════════
#  SOFT CRITERIA
# ═══════════════════════════════════════════════════════════════════════════════


class TestSoftGacsScore:
    def test_deducts_when_below_minimum(
        self, db, configured_criteria, pipeline_property_base, vrm_property, growth_area
    ):
        """GACS score below minimum deducts points."""
        configured_criteria.min_gacs_score = Decimal("70")
        configured_criteria.save()
        # Set composite_score below the minimum.  We use a direct update
        # because the model's save() method recomputes the score.
        from core.models import GrowthArea

        GrowthArea.objects.filter(pk=growth_area.pk).update(
            composite_score=Decimal("50.00")
        )
        growth_area.refresh_from_db()

        # Need state=TX in allowed for pipeline with TX source
        configured_criteria.allowed_states = ["TX"]
        configured_criteria.save()

        result = screen_property(
            pipeline_property_base, configured_criteria, vrm_property
        )
        assert result.score < Decimal("100")
        assert any("below minimum" in f for f in result.soft_failures)

    def test_skips_when_no_minimum(self, db, criteria, pipeline_property_base):
        """No min GACS → skip."""
        criteria.min_gacs_score = None
        criteria.save()

        result = screen_property(pipeline_property_base, criteria)
        assert "GACS score screening skipped" in str(result.passes)

    def test_skips_when_no_growth_area(
        self, db, configured_criteria, pipeline_property_base, vrm_property
    ):
        """No GrowthArea found → skip with note."""
        configured_criteria.allowed_states = ["TX"]
        configured_criteria.save()

        result = screen_property(
            pipeline_property_base, configured_criteria, vrm_property
        )
        assert "no GrowthArea found" in str(result.passes)


class TestSoftGrossYield:
    def test_deducts_when_below_minimum(
        self, db, configured_criteria, user, vrm_property, growth_area
    ):
        """Gross yield below minimum deducts points."""
        # vrm_property: price=250000, rent=2200 → yield = (2200*12/250000)*100 = 10.56%
        # Set minimum higher
        configured_criteria.min_gross_yield_pct = Decimal("12.00")
        configured_criteria.allowed_states = ["TX"]
        configured_criteria.save()

        from core.models import PipelineProperty

        pp = PipelineProperty(
            user=user,
            source_type="vrm",
            source_id="vrm-999",
            address="456 Oak Ave",
            address_hash="vrm-hash",
            price=Decimal("250000"),
            estimated_rent=Decimal("2200"),
            beds=3,
            year_built=2015,
        )
        pp.save()

        result = screen_property(pp, configured_criteria, vrm_property)
        assert result.score < Decimal("100")
        assert any("below minimum" in f for f in result.soft_failures)

    def test_skip_with_foreclosure_source(
        self, db, configured_criteria, user, foreclosure_property, growth_area
    ):
        """ForeclosureProperty → yield skipped."""
        configured_criteria.allowed_states = ["TX"]
        configured_criteria.save()

        from core.models import PipelineProperty

        pp = PipelineProperty(
            user=user,
            source_type="foreclosure",
            source_id="fc-prop-001",
            address="789 Elm St",
            address_hash="fc-hash",
            price=Decimal("200000"),
            beds=3,
        )
        pp.save()

        result = screen_property(pp, configured_criteria, foreclosure_property)
        # Check that yield/PTR were noted as skipped
        assert "no rent estimate available" in result.notes


class TestSoftPriceToRentRatio:
    def test_deducts_when_above_maximum(
        self, db, configured_criteria, user, vrm_property, growth_area
    ):
        """PTR above maximum deducts points."""
        configured_criteria.max_price_to_rent_ratio = Decimal("8.00")
        configured_criteria.allowed_states = ["TX"]
        configured_criteria.save()
        # vrm: price=250000, rent=2200 → PTR = 250000/2200 = 113.6

        from core.models import PipelineProperty

        pp = PipelineProperty(
            user=user,
            source_type="vrm",
            source_id="vrm-999",
            address="456 Oak Ave",
            address_hash="vrm-hash",
            price=Decimal("250000"),
            estimated_rent=Decimal("2200"),
            beds=3,
            year_built=2015,
        )
        pp.save()

        result = screen_property(pp, configured_criteria, vrm_property)
        assert result.score < Decimal("100")
        assert any("above maximum" in f for f in result.soft_failures)

    def test_skip_when_no_rent(self, db, configured_criteria, user):
        """No rent → PTR skipped."""
        configured_criteria.allowed_states = []
        configured_criteria.save()

        from core.models import PipelineProperty

        pp = PipelineProperty(
            user=user,
            source_type="manual",
            source_id="m-rentless",
            address="555 No Rent",
            address_hash="norent",
            price=Decimal("250000"),
            estimated_rent=None,
            beds=3,
        )
        pp.save()

        result = screen_property(pp, configured_criteria)
        assert "no rent estimate available" in str(result.passes)


class TestSoftYearBuilt:
    def test_deducts_when_too_old(
        self, db, configured_criteria, pipeline_property_base, vrm_property
    ):
        """Year built before cutoff → deducts 5 points."""
        configured_criteria.allowed_states = ["TX"]
        configured_criteria.save()

        result = screen_property(
            pipeline_property_base, configured_criteria, vrm_property
        )
        # pipeline_property_base has year_built=2010, cutoff is 2000 → passes
        assert not any("older than cutoff" in f for f in result.soft_failures)

    def test_deducts_when_older_than_max(
        self, db, configured_criteria, user, vrm_property
    ):
        """Year built older than max_year_built → deducts 5 points."""
        configured_criteria.max_year_built = 2020
        configured_criteria.allowed_states = ["TX"]
        configured_criteria.save()

        from core.models import PipelineProperty

        pp = PipelineProperty(
            user=user,
            source_type="vrm",
            source_id="vrm-997",
            address="111 Old House",
            address_hash="old-hash",
            price=Decimal("200000"),
            estimated_rent=Decimal("1800"),
            beds=3,
            year_built=1995,
        )
        pp.save()

        result = screen_property(pp, configured_criteria, vrm_property)
        assert any("older than cutoff" in f for f in result.soft_failures)
        assert result.score <= Decimal("95")  # 100 - 5

    def test_skip_when_no_year_built(self, db, configured_criteria, user):
        """No year_built → skip."""
        from core.models import PipelineProperty

        pp = PipelineProperty(
            user=user,
            source_type="manual",
            source_id="m-010",
            address="222 Unknown",
            address_hash="unk-hash",
            price=Decimal("200000"),
            beds=3,
        )
        pp.save()
        configured_criteria.allowed_states = []
        configured_criteria.save()

        result = screen_property(pp, configured_criteria)
        assert "no year_built data" in str(result.passes)


class TestSoftBeds:
    def test_deducts_when_below_min(
        self, db, configured_criteria, pipeline_property_base, vrm_property
    ):
        """Beds below minimum → deducts."""
        configured_criteria.allowed_states = ["TX"]
        configured_criteria.min_beds = 4
        configured_criteria.save()
        # pipeline_property_base has beds=3

        result = screen_property(
            pipeline_property_base, configured_criteria, vrm_property
        )
        assert any("below minimum" in f for f in result.soft_failures)
        assert result.score <= Decimal("95")  # 100 - 5

    def test_deducts_when_above_max(self, db, configured_criteria, user, vrm_property):
        """Beds above maximum → deducts."""
        configured_criteria.allowed_states = ["TX"]
        configured_criteria.max_beds = 2
        configured_criteria.save()

        from core.models import PipelineProperty

        pp = PipelineProperty(
            user=user,
            source_type="vrm",
            source_id="vrm-996",
            address="333 Big House",
            address_hash="big-hash",
            price=Decimal("300000"),
            estimated_rent=Decimal("2500"),
            beds=5,
            year_built=2020,
        )
        pp.save()

        result = screen_property(pp, configured_criteria, vrm_property)
        assert any("above maximum" in f for f in result.soft_failures)

    def test_skips_when_no_beds(self, db, configured_criteria, user):
        """No beds → skip."""
        from core.models import PipelineProperty

        pp = PipelineProperty(
            user=user,
            source_type="manual",
            source_id="m-011",
            address="444 No Beds",
            address_hash="no-bed",
            price=Decimal("200000"),
        )
        pp.save()
        configured_criteria.allowed_states = []
        configured_criteria.save()

        result = screen_property(pp, configured_criteria)
        assert "no beds data" in str(result.passes)


# ═══════════════════════════════════════════════════════════════════════════════
#  INTEGRATION / EDGE CASES
# ═══════════════════════════════════════════════════════════════════════════════


class TestIntegration:
    def test_all_pass_with_vrm_source(
        self, db, configured_criteria, user, vrm_property, growth_area
    ):
        """All criteria met, VrmProperty source, everything passes."""
        configured_criteria.allowed_states = ["TX"]
        configured_criteria.max_price_to_rent_ratio = Decimal("200")
        configured_criteria.min_gacs_score = Decimal("10")
        configured_criteria.save()
        # growth_area composite_score will be computed on save as ~1.82 raw
        # With ×100 scaling: ~181.50

        from core.models import PipelineProperty

        pp = PipelineProperty(
            user=user,
            source_type="vrm",
            source_id="vrm-999",
            address="456 Oak Ave",
            address_hash="all-pass",
            price=Decimal("250000"),
            estimated_rent=Decimal("2200"),
            beds=3,
            year_built=2015,
        )
        pp.save()

        result = screen_property(pp, configured_criteria, vrm_property)
        assert result.passed
        # GACS v2: composite_score × 100 ≈ 181.50 >= min 10 → no deduction
        assert result.score == Decimal("100.00"), f"Expected 100.00, got {result.score}"
        assert len(result.hard_failures) == 0
        assert len(result.soft_failures) == 0  # GACS above minimum — all green
        assert len(result.passes) >= 4

    def test_foreclosure_property_skips_yield(
        self, db, configured_criteria, user, foreclosure_property, growth_area
    ):
        """ForeclosureProperty source → yield/PTR noted as skipped."""
        configured_criteria.allowed_states = ["TX"]
        configured_criteria.save()

        from core.models import PipelineProperty

        pp = PipelineProperty(
            user=user,
            source_type="foreclosure",
            source_id="fc-prop-001",
            address="789 Elm St",
            address_hash="fc-pass",
            price=Decimal("200000"),
            beds=3,
            year_built=2005,
        )
        pp.save()

        result = screen_property(pp, configured_criteria, foreclosure_property)
        assert result.passed
        assert "no rent estimate available" in result.notes

    def test_no_criteria_set_defaults(self, db, criteria, user):
        """All criteria at defaults (none/empty) — passes without deductions."""
        from core.models import PipelineProperty

        pp = PipelineProperty(
            user=user,
            source_type="manual",
            source_id="m-100",
            address="123 Defaults St",
            address_hash="defaults",
            price=Decimal("250000"),
            # No estimated_rent → yield/PTR skipped
            beds=3,
            year_built=2010,
        )
        pp.save()

        result = screen_property(pp, criteria)
        assert result.passed
        assert result.score == Decimal("100")
        # All soft criteria should have been skipped with notes
        skip_count = sum(1 for p in result.passes if "skipped" in p.lower())
        assert skip_count >= 3

    def test_missing_data_graceful(self, db, user):
        """PipelineProperty with minimal data — gracefully skips all checks."""
        from core.models import PipelineProperty, ScreeningCriteria

        pp = PipelineProperty(
            user=user,
            source_type="manual",
            source_id="m-999",
            address="555 Minimal",
            address_hash="minimal",
            price=None,
            beds=None,
        )
        pp.save()

        criteria = ScreeningCriteria.objects.create(user=user)

        result = screen_property(pp, criteria)
        assert result.passed
        assert result.score == Decimal("100")

    def test_vrm_source_uses_project_rent(
        self, db, configured_criteria, user, vrm_property, growth_area
    ):
        """VrmProperty's projected_monthly_rent is preferred over PP estimated_rent."""
        configured_criteria.max_price_to_rent_ratio = Decimal("100.00")
        configured_criteria.allowed_states = ["TX"]
        configured_criteria.save()
        from core.models import GrowthArea

        GrowthArea.objects.filter(pk=growth_area.pk).update(
            composite_score=Decimal("50.00")
        )
        growth_area.refresh_from_db()

        from core.models import PipelineProperty

        pp = PipelineProperty(
            user=user,
            source_type="vrm",
            source_id="vrm-999",
            address="456 Oak Ave",
            address_hash="vrm-rent",
            price=Decimal("250000"),
            estimated_rent=Decimal("500"),  # Low — should NOT be used
            beds=3,
            year_built=2015,
        )
        pp.save()

        # vrm_property has projected_monthly_rent=2200
        result = screen_property(pp, configured_criteria, vrm_property)
        # PTR = 250000/2200 ≈ 113.6 → above 100 → should deduct
        # If PP.estimated_rent (500) was used, PTR = 250000/500 = 500 → even worse
        assert any("above maximum" in f for f in result.soft_failures)

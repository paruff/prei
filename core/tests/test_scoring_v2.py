"""Tests for score_listing_v2 underwriting score."""

from decimal import Decimal

import pytest

from core.models import Property, UserInvestmentTargets, UserProfile
from core.services.scoring import UnderwritingScore, score_listing_v2


@pytest.fixture
def user(db):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    return User.objects.create_user(username="scorer", password="pass")


@pytest.fixture
def targets(db, user):
    """Default UserInvestmentTargets with standard thresholds."""
    return UserInvestmentTargets.objects.create(
        user=user,
        min_coc_pct=Decimal("0.08"),
        min_dscr=Decimal("1.25"),
        max_grm=Decimal("12.00"),
        require_one_pct_rule=True,
        target_hold_years=7,
        marginal_tax_rate=Decimal("0.24"),
    )


@pytest.fixture
def profile(db, user):
    """UserProfile with default land_value_pct."""
    return UserProfile.objects.create(
        user=user,
        marginal_tax_rate=Decimal("0.24"),
        land_value_pct=Decimal("0.20"),
    )


@pytest.fixture
def strong_property(db, user):
    """A property that should score well — 1% rule passes, good CoC/DSCR."""
    return Property.objects.create(
        user=user,
        address="100 Strong Ave",
        city="Austin",
        state="TX",
        zip_code="78702",
        purchase_price=Decimal("200000"),
        monthly_rent_gross=Decimal("2500"),  # 1.25% ratio — passes 1% rule
        property_taxes_annual=Decimal("2400"),
        insurance_annual=Decimal("1200"),
        hoa_monthly=Decimal("0"),
        maintenance_monthly=Decimal("100"),
        capex_monthly=Decimal("50"),
        down_payment_pct=Decimal("0.20"),
        interest_rate=Decimal("0.06"),
        loan_term_years=30,
        vacancy_rate=Decimal("0.05"),
        mgmt_fee_pct=Decimal("0.08"),
    )


@pytest.fixture
def weak_property(db, user):
    """A property that should score poorly — fails 1% rule, low CoC."""
    return Property.objects.create(
        user=user,
        address="200 Weak Blvd",
        city="Denver",
        state="CO",
        zip_code="80202",
        purchase_price=Decimal("500000"),
        monthly_rent_gross=Decimal("2000"),  # 0.4% — fails 1% rule badly
        property_taxes_annual=Decimal("6000"),
        insurance_annual=Decimal("2400"),
        hoa_monthly=Decimal("200"),
        maintenance_monthly=Decimal("300"),
        capex_monthly=Decimal("200"),
        down_payment_pct=Decimal("0.25"),
        interest_rate=Decimal("0.07"),
        loan_term_years=30,
        vacancy_rate=Decimal("0.10"),
        mgmt_fee_pct=Decimal("0.10"),
    )


@pytest.fixture
def zero_rent_property(db, user):
    """Edge case: property with $0 rent."""
    return Property.objects.create(
        user=user,
        address="300 Empty Rd",
        city="Dallas",
        state="TX",
        zip_code="75201",
        purchase_price=Decimal("150000"),
        monthly_rent_gross=Decimal("0"),
        property_taxes_annual=Decimal("1800"),
        insurance_annual=Decimal("900"),
        hoa_monthly=Decimal("0"),
        maintenance_monthly=Decimal("100"),
        capex_monthly=Decimal("50"),
        down_payment_pct=Decimal("0.20"),
        interest_rate=Decimal("0.07"),
        loan_term_years=30,
        vacancy_rate=Decimal("0.08"),
        mgmt_fee_pct=Decimal("0.10"),
    )


# ── Basic field population ────────────────────────────────────────────────────


class TestScoreListingV2Fields:
    """All UnderwritingScore fields must be populated."""

    def test_returns_dataclass(self, strong_property, targets, profile):
        result = score_listing_v2(strong_property, targets)
        assert isinstance(result, UnderwritingScore)

    def test_total_score_range(self, strong_property, targets, profile):
        result = score_listing_v2(strong_property, targets)
        assert 0 <= result.total_score <= 100

    def test_one_pct_ratio_populated(self, strong_property, targets, profile):
        result = score_listing_v2(strong_property, targets)
        expected = Decimal("2500") / Decimal("200000")
        assert result.one_pct_ratio == expected.quantize(Decimal("0.01"))

    def test_cap_rate_populated(self, strong_property, targets, profile):
        result = score_listing_v2(strong_property, targets)
        assert result.cap_rate > 0

    def test_cash_on_cash_populated(self, strong_property, targets, profile):
        result = score_listing_v2(strong_property, targets)
        assert result.cash_on_cash != 0

    def test_dscr_populated(self, strong_property, targets, profile):
        result = score_listing_v2(strong_property, targets)
        assert result.dscr > 0

    def test_grm_populated(self, strong_property, targets, profile):
        result = score_listing_v2(strong_property, targets)
        assert result.grm > 0

    def test_after_tax_coc_populated(self, strong_property, targets, profile):
        result = score_listing_v2(strong_property, targets)
        assert isinstance(result.after_tax_coc, Decimal)

    def test_verdict_populated(self, strong_property, targets, profile):
        result = score_listing_v2(strong_property, targets)
        assert result.verdict in ("Strong Buy", "Conditional", "Pass")

    def test_flags_is_list(self, strong_property, targets, profile):
        result = score_listing_v2(strong_property, targets)
        assert isinstance(result.flags, list)

    def test_score_breakdown_sum(self, strong_property, targets, profile):
        result = score_listing_v2(strong_property, targets)
        breakdown_sum = (
            result.score_1pct
            + result.score_coc
            + result.score_dscr
            + result.score_cap
            + result.score_grm
            + result.score_after_tax
        )
        # Breakdown sum may differ from total due to 1% rule cap
        assert breakdown_sum >= result.total_score


# ── Determinism ───────────────────────────────────────────────────────────────


class TestScoreDeterminism:
    """Same inputs must always produce the same score."""

    def test_deterministic(self, strong_property, targets, profile):
        r1 = score_listing_v2(strong_property, targets)
        r2 = score_listing_v2(strong_property, targets)
        assert r1.total_score == r2.total_score
        assert r1.verdict == r2.verdict
        assert r1.flags == r2.flags


# ── 1% Rule ───────────────────────────────────────────────────────────────────


class TestOnePercentRule:
    """1% Rule: monthly_rent / purchase_price >= 0.01 → 20 points."""

    def test_passes_1pct_rule(self, strong_property, targets, profile):
        result = score_listing_v2(strong_property, targets)
        assert result.passes_one_pct_rule is True
        assert result.score_1pct == 20

    def test_fails_1pct_rule(self, weak_property, targets, profile):
        result = score_listing_v2(weak_property, targets)
        assert result.passes_one_pct_rule is False
        assert result.score_1pct == 0
        assert any("1% Rule" in f for f in result.flags)

    def test_exactly_1pct(self, db, user, targets, profile):
        """Exactly 1.0% should pass."""
        prop = Property.objects.create(
            user=user,
            address="Exact Pct",
            city="Austin",
            state="TX",
            zip_code="78702",
            purchase_price=Decimal("100000"),
            monthly_rent_gross=Decimal("1000"),
            property_taxes_annual=Decimal("1200"),
            insurance_annual=Decimal("600"),
            hoa_monthly=Decimal("0"),
            maintenance_monthly=Decimal("50"),
            capex_monthly=Decimal("25"),
            down_payment_pct=Decimal("0.20"),
            interest_rate=Decimal("0.07"),
            loan_term_years=30,
            vacancy_rate=Decimal("0.08"),
            mgmt_fee_pct=Decimal("0.10"),
        )
        result = score_listing_v2(prop, targets)
        assert result.passes_one_pct_rule is True

    def test_cap_at_40_when_1pct_fails(self, weak_property, targets, profile):
        """When require_one_pct_rule is True and 1% fails, score capped at 40."""
        assert targets.require_one_pct_rule is True
        result = score_listing_v2(weak_property, targets)
        assert result.total_score <= 40


# ── CoC scoring ───────────────────────────────────────────────────────────────


class TestCoCScoring:
    """Cash-on-Cash: partial credit based on actual/target ratio."""

    def test_coc_above_target(self, strong_property, targets, profile):
        result = score_listing_v2(strong_property, targets)
        # If CoC >= 8%, should get full 25 points
        if result.cash_on_cash >= targets.min_coc_pct:
            assert result.score_coc == 25

    def test_negative_coc_flag(self, weak_property, targets, profile):
        result = score_listing_v2(weak_property, targets)
        if result.cash_on_cash < Decimal("0"):
            assert any("Negative Cash-on-Cash" in f for f in result.flags)


# ── DSCR scoring ──────────────────────────────────────────────────────────────


class TestDSCRScoring:
    """DSCR: partial credit based on actual/target ratio."""

    def test_dscr_above_target(self, strong_property, targets, profile):
        result = score_listing_v2(strong_property, targets)
        if result.dscr >= targets.min_dscr:
            assert result.score_dscr == 20

    def test_dscr_below_target_flag(self, weak_property, targets, profile):
        result = score_listing_v2(weak_property, targets)
        if result.dscr < targets.min_dscr:
            assert any("DSCR" in f and "below" in f for f in result.flags)


# ── Cap rate scoring ──────────────────────────────────────────────────────────


class TestCapRateScoring:
    """Cap rate: partial credit toward 6% target."""

    def test_cap_rate_full_points(self, strong_property, targets, profile):
        result = score_listing_v2(strong_property, targets)
        if result.cap_rate >= Decimal("0.06"):
            assert result.score_cap == 15


# ── GRM scoring ───────────────────────────────────────────────────────────────


class TestGRMScoring:
    """GRM: lower is better; partial credit up to 10 points."""

    def test_grm_within_target(self, strong_property, targets, profile):
        result = score_listing_v2(strong_property, targets)
        if result.grm <= targets.max_grm:
            assert result.score_grm == 10

    def test_grm_exceeds_target_flag(self, weak_property, targets, profile):
        result = score_listing_v2(weak_property, targets)
        if result.grm > targets.max_grm:
            assert any("GRM" in f and "exceeds" in f for f in result.flags)


# ── After-tax bonus ───────────────────────────────────────────────────────────


class TestAfterTaxBonus:
    """After-tax CoC: 10 bonus points if positive."""

    def test_positive_after_tax_gets_bonus(self, strong_property, targets, profile):
        result = score_listing_v2(strong_property, targets)
        if result.after_tax_coc > Decimal("0"):
            assert result.score_after_tax == 10


# ── Verdict mapping ───────────────────────────────────────────────────────────


class TestVerdictMapping:
    """Verdict must map to score ranges."""

    def test_verdict_matches_score(self, strong_property, targets, profile):
        result = score_listing_v2(strong_property, targets)
        if result.total_score >= 75:
            assert result.verdict == "Strong Buy"
        elif result.total_score >= 50:
            assert result.verdict == "Conditional"
        else:
            assert result.verdict == "Pass"

    def test_weak_property_pass(self, weak_property, targets, profile):
        result = score_listing_v2(weak_property, targets)
        assert result.verdict == "Pass"
        assert result.total_score < 50


# ── Flags ─────────────────────────────────────────────────────────────────────


class TestFlags:
    """Flags list must be non-empty when any criterion fails."""

    def test_weak_property_has_flags(self, weak_property, targets, profile):
        result = score_listing_v2(weak_property, targets)
        assert len(result.flags) > 0

    def test_strong_property_fewer_flags(self, strong_property, targets, profile):
        result = score_listing_v2(strong_property, targets)
        # Strong property should have 0-2 flags
        assert len(result.flags) <= 2


# ── Edge case: rent = 0 ──────────────────────────────────────────────────────


class TestZeroRent:
    """Edge case: property with $0 rent."""

    def test_zero_rent_zero_score(self, zero_rent_property, targets, profile):
        result = score_listing_v2(zero_rent_property, targets)
        assert result.total_score == 0
        assert result.verdict == "Pass"
        assert result.passes_one_pct_rule is False
        assert any("1% Rule" in f for f in result.flags)
        assert any("Negative" in f for f in result.flags)


# ── Perfect score scenario ────────────────────────────────────────────────────


class TestPerfectScore:
    """A near-perfect property should score 75+ (Strong Buy)."""

    def test_perfect_property(self, db, user, targets, profile):
        """Create an ideal property: high rent, low price, low expenses."""
        prop = Property.objects.create(
            user=user,
            address="999 Perfect Ln",
            city="Austin",
            state="TX",
            zip_code="78702",
            purchase_price=Decimal("100000"),
            monthly_rent_gross=Decimal("2000"),  # 2% rule — very strong
            property_taxes_annual=Decimal("800"),
            insurance_annual=Decimal("400"),
            hoa_monthly=Decimal("0"),
            maintenance_monthly=Decimal("50"),
            capex_monthly=Decimal("25"),
            down_payment_pct=Decimal("0.20"),
            interest_rate=Decimal("0.05"),
            loan_term_years=30,
            vacancy_rate=Decimal("0.03"),
            mgmt_fee_pct=Decimal("0.05"),
        )
        result = score_listing_v2(prop, targets)
        assert result.total_score >= 75
        assert result.verdict == "Strong Buy"
        assert result.passes_one_pct_rule is True


# ── Score range edge cases ────────────────────────────────────────────────────


class TestScoreRange:
    """Total score stays within [0, 100]."""

    def test_score_never_negative(self, zero_rent_property, targets, profile):
        result = score_listing_v2(zero_rent_property, targets)
        assert result.total_score >= 0

    def test_score_never_above_100(self, strong_property, targets, profile):
        result = score_listing_v2(strong_property, targets)
        assert result.total_score <= 100

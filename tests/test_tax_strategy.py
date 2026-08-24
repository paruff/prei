"""Tests for tax strategy module (QBI, PAL, 1031 Exchange)."""

from decimal import Decimal

from investor_app.finance.tax_strategy import (
    calculate_qbi_deduction,
    calculate_pal_allowance,
    calculate_1031_exchange,
    calculate_1031_deferral_ratio,
    calculate_pal_phase_out,
    calculate_total_tax_benefit,
    PAL_FULL_ALLOWANCE,
)


class TestQBI:
    """Tests for Qualified Business Income (QBI) deduction."""

    def test_qbi_deduction_basic(self) -> None:
        """Test basic QBI deduction calculation."""
        result = calculate_qbi_deduction(
            qualified_business_income=Decimal("50000"),
            w2_wages=Decimal("0"),
            qbi_adjusted_basis=Decimal("0"),
        )
        # 20% of $50,000 = $10,000
        assert result == Decimal("10000.00")

    def test_qbi_deduction_with_w2_limit(self) -> None:
        """Test QBI deduction with W-2 wage limitation."""
        # For high-income taxpayers, QBI deduction is limited to 50% of W-2 wages
        result = calculate_qbi_deduction(
            qualified_business_income=Decimal("200000"),
            w2_wages=Decimal("50000"),
            qbi_adjusted_basis=Decimal("0"),
            taxable_income=Decimal("300000"),  # Above phase-out
        )
        # 50% of W-2 wages = $25,000 (which is less than 20% of income = $40,000)
        assert result == Decimal("25000.00")

    def test_qbi_deduction_with_basis_limit(self) -> None:
        """Test QBI deduction with qualified property limitation."""
        # 2.5% of QBI adjusted basis
        result = calculate_qbi_deduction(
            qualified_business_income=Decimal("100000"),
            w2_wages=Decimal("0"),
            qbi_adjusted_basis=Decimal("400000"),
            taxable_income=Decimal("300000"),
        )
        # 2.5% of $400,000 = $10,000
        assert result == Decimal("10000.00")

    def test_qbi_deduction_below_phaseout(self) -> None:
        """Test QBI deduction for income below phase-out threshold."""
        result = calculate_qbi_deduction(
            qualified_business_income=Decimal("100000"),
            w2_wages=Decimal("30000"),
            qbi_adjusted_basis=Decimal("200000"),
            taxable_income=Decimal("150000"),  # Below $164,900 for single
        )
        # No phase-out, full 20% deduction
        assert result == Decimal("20000.00")

    def test_qbi_deduction_zero_income(self) -> None:
        """Test QBI deduction with zero income."""
        result = calculate_qbi_deduction(
            qualified_business_income=Decimal("0"),
            w2_wages=Decimal("0"),
            qbi_adjusted_basis=Decimal("0"),
        )
        assert result == Decimal("0")


class TestPAL:
    """Tests for Passive Activity Loss (PAL) rules."""

    def test_pal_full_allowance_below_threshold(self) -> None:
        """Test PAL allowance for income below $100k threshold."""
        result = calculate_pal_allowance(
            active_participation=Decimal("1"),
            modified_agi=Decimal("80000"),
            rental_losses=Decimal("25000"),
        )
        # Full $25,000 allowance for active participation
        assert result == PAL_FULL_ALLOWANCE

    def test_pal_zero_for_inactive_participation(self) -> None:
        """Test PAL allowance is zero for non-active participation."""
        result = calculate_pal_allowance(
            active_participation=Decimal("0"),
            modified_agi=Decimal("80000"),
            rental_losses=Decimal("25000"),
        )
        assert result == Decimal("0")

    def test_pal_phase_out(self) -> None:
        """Test PAL phase-out between $100k-$150k AGI."""
        # $125k AGI = midpoint between $100k and $150k = 50% reduction
        phase_out = calculate_pal_phase_out(Decimal("125000"))
        assert phase_out == Decimal("0.50")

    def test_pal_phase_out_below_threshold(self) -> None:
        """Test PAL phase-out below $100k AGI."""
        phase_out = calculate_pal_phase_out(Decimal("80000"))
        assert phase_out == Decimal("1")

    def test_pal_phase_out_above_threshold(self) -> None:
        """Test PAL phase-out above $150k AGI."""
        phase_out = calculate_pal_phase_out(Decimal("200000"))
        assert phase_out == Decimal("0")

    def test_pal_max_losses(self) -> None:
        """Test PAL deductibility capped at losses."""
        result = calculate_pal_allowance(
            active_participation=Decimal("1"),
            modified_agi=Decimal("50000"),
            rental_losses=Decimal("30000"),  # Greater than $25k cap
        )
        # Capped at $25,000 maximum
        assert result == PAL_FULL_ALLOWANCE


class Test1031Exchange:
    """Tests for 1031 Exchange calculations."""

    def test_basic_deferral(self) -> None:
        """Test basic 1031 exchange deferral."""
        result = calculate_1031_exchange(
            sale_price=Decimal("500000"),
            original_cost_basis=Decimal("300000"),
            accumulated_depreciation=Decimal("45000"),
            replacement_price=Decimal("600000"),
            selling_costs=Decimal("30000"),
        )
        # All gains deferred if replacement price >= sale price
        assert result["deferred_gain"] == Decimal("200000")

    def test_partial_deferral(self) -> None:
        """Test 1031 exchange with partial deferral."""
        result = calculate_1031_exchange(
            sale_price=Decimal("500000"),
            original_cost_basis=Decimal("300000"),
            accumulated_depreciation=Decimal("45000"),
            replacement_price=Decimal("400000"),
            selling_costs=Decimal("30000"),
        )
        # Partial deferral: replacement price < sale price
        assert result["deferred_gain"] < Decimal("200000")
        assert result["boot_received"] > Decimal("0")

    def test_deferral_ratio(self) -> None:
        """Test deferral ratio calculation."""
        ratio = calculate_1031_deferral_ratio(
            sale_price=Decimal("500000"),
            replacement_price=Decimal("500000"),
            selling_costs=Decimal("30000"),
        )
        # 100% deferral if replacement price covers net sale price
        assert ratio == Decimal("1")

    def test_partial_deferral_ratio(self) -> None:
        """Test partial deferral ratio."""
        ratio = calculate_1031_deferral_ratio(
            sale_price=Decimal("500000"),
            replacement_price=Decimal("450000"),
            selling_costs=Decimal("30000"),
        )
        # 450000 / (500000 - 30000) = 0.957...
        expected = Decimal("450000") / (Decimal("500000") - Decimal("30000"))
        assert abs(ratio - expected) < Decimal("0.01")

    def test_total_tax_benefit(self) -> None:
        """Test total tax benefit calculation."""
        benefit = calculate_total_tax_benefit(
            qbi_income=Decimal("50000"),
            rental_losses=Decimal("20000"),
            modified_agi=Decimal("80000"),
            marginal_tax_rate=Decimal("0.24"),
        )
        # QBI deduction = 20% of $50,000 = $10,000
        # PAL = $20,000 (full allowance)
        # Total tax benefit = ($10,000 + $20,000) * 0.24 = $7,200
        assert benefit == Decimal("7200.00")

    def test_total_tax_benefit_with_phase_out(self) -> None:
        """Test total tax benefit with PAL phase-out."""
        benefit = calculate_total_tax_benefit(
            qbi_income=Decimal("100000"),
            rental_losses=Decimal("25000"),
            modified_agi=Decimal("125000"),  # Midpoint = 50% reduction
            marginal_tax_rate=Decimal("0.24"),
        )
        # QBI deduction = 20% of $100,000 = $20,000
        # PAL = $25,000 * 0.50 = $12,500 (50% reduction)
        # Total tax benefit = ($20,000 + $12,500) * 0.24 = $7,800
        assert benefit == Decimal("7800.00")

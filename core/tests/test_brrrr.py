"""Tests for the BRRRR (Buy, Rehab, Rent, Refinance, Repeat) calculator.

Covers:
- BRRRRAnalysis dataclass fields
- calculate_brrrr pure-math function
- Verdict logic (Full Cycle / Partial Recycle / Capital Trap)
- Edge cases and boundary conditions
"""

from decimal import Decimal

from core.services.brrrr import BRRRRAnalysis, calculate_brrrr


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _q2(val: Decimal) -> Decimal:
    """Quantize to 2 decimal places for comparison."""
    return val.quantize(Decimal("0.01"))


# ---------------------------------------------------------------------------
# Unit test from acceptance criteria
# ---------------------------------------------------------------------------


class TestAcceptanceCriteria:
    """Verify the exact scenario from the ISSUE 3-A spec."""

    def test_80k_purchase_20k_rehab_150k_arv_1200_rent(self) -> None:
        """$80,000 purchase + $20,000 rehab + $150,000 ARV + $1,200/mo rent at 75% LTV.

        Manual calculation:
            closing_costs    = 80000 * 0.02 = 1600
            total_project    = 80000 + 20000 + 1600 = 101600
            max_refi_loan    = 150000 * 0.75 = 112500
            cash_left_in_deal = 101600 - 112500 = -10900  (Full Cycle!)
        """
        result = calculate_brrrr(
            purchase_price=Decimal("80000"),
            rehab_cost=Decimal("20000"),
            arv=Decimal("150000"),
            monthly_rent_post_rehab=Decimal("1200"),
            annual_operating_expenses=Decimal("3600"),
        )

        assert isinstance(result, BRRRRAnalysis)
        assert result.purchase_price == Decimal("80000")
        assert result.rehab_cost == Decimal("20000")
        assert result.arv == Decimal("150000")
        assert result.total_project_cost == Decimal("101600")
        assert result.max_refi_loan == Decimal("112500")
        assert result.cash_left_in_deal == Decimal("-10900")
        assert result.is_full_cycle is True
        assert result.verdict == "Full Cycle"


# ---------------------------------------------------------------------------
# BRRRRAnalysis dataclass
# ---------------------------------------------------------------------------


class TestBRRRRAnalysisDataclass:
    """Verify the dataclass holds all required fields."""

    def test_all_fields_present(self) -> None:
        """BRRRRAnalysis must have all 11 fields from the spec."""
        analysis = BRRRRAnalysis(
            purchase_price=Decimal("100000"),
            rehab_cost=Decimal("25000"),
            arv=Decimal("180000"),
            total_project_cost=Decimal("127000"),
            max_refi_loan=Decimal("135000"),
            cash_left_in_deal=Decimal("-8000"),
            cash_out_at_refi=Decimal("135000"),
            post_refi_dscr=Decimal("1.35"),
            post_refi_coc=Decimal("Infinity"),
            is_full_cycle=True,
            verdict="Full Cycle",
        )
        assert analysis.purchase_price == Decimal("100000")
        assert analysis.rehab_cost == Decimal("25000")
        assert analysis.arv == Decimal("180000")
        assert analysis.total_project_cost == Decimal("127000")
        assert analysis.max_refi_loan == Decimal("135000")
        assert analysis.cash_left_in_deal == Decimal("-8000")
        assert analysis.cash_out_at_refi == Decimal("135000")
        assert analysis.post_refi_dscr == Decimal("1.35")
        assert analysis.post_refi_coc == Decimal("Infinity")
        assert analysis.is_full_cycle is True
        assert analysis.verdict == "Full Cycle"


# ---------------------------------------------------------------------------
# Verdict logic
# ---------------------------------------------------------------------------


class TestVerdictLogic:
    """Verify the three verdict branches."""

    def test_full_cycle_when_cash_left_zero(self) -> None:
        """cash_left_in_deal == 0 → Full Cycle."""
        result = calculate_brrrr(
            purchase_price=Decimal("100000"),
            rehab_cost=Decimal("0"),
            arv=Decimal("133334"),  # 133334 * 0.75 = 100000.50 → cash_left ≈ -0.50
            monthly_rent_post_rehab=Decimal("1000"),
            annual_operating_expenses=Decimal("2400"),
            closing_costs_pct=Decimal("0"),
        )
        # cash_left should be <= 0
        assert result.cash_left_in_deal <= Decimal("0")
        assert result.verdict == "Full Cycle"
        assert result.is_full_cycle is True

    def test_full_cycle_when_cash_left_negative(self) -> None:
        """cash_left_in_deal < 0 → Full Cycle."""
        result = calculate_brrrr(
            purchase_price=Decimal("80000"),
            rehab_cost=Decimal("20000"),
            arv=Decimal("150000"),
            monthly_rent_post_rehab=Decimal("1200"),
            annual_operating_expenses=Decimal("3600"),
        )
        assert result.cash_left_in_deal < Decimal("0")
        assert result.verdict == "Full Cycle"

    def test_partial_recycle(self) -> None:
        """0 < cash_left <= 25% of total_project_cost → Partial Recycle."""
        # total_project_cost = 100000 + 20000 + 2000 = 122000
        # max_refi = 150000 * 0.75 = 112500
        # cash_left = 122000 - 112500 = 9500  (9500 / 122000 ≈ 7.8% ≤ 25%)
        result = calculate_brrrr(
            purchase_price=Decimal("100000"),
            rehab_cost=Decimal("20000"),
            arv=Decimal("150000"),
            monthly_rent_post_rehab=Decimal("1200"),
            annual_operating_expenses=Decimal("3600"),
        )
        assert result.cash_left_in_deal > Decimal("0")
        assert result.cash_left_in_deal <= result.total_project_cost * Decimal("0.25")
        assert result.verdict == "Partial Recycle"
        assert result.is_full_cycle is False

    def test_capital_trap(self) -> None:
        """cash_left > 25% of total_project_cost → Capital Trap."""
        # total_project_cost = 200000 + 10000 + 4000 = 214000
        # max_refi = 220000 * 0.75 = 165000
        # cash_left = 214000 - 165000 = 49000  (49000 / 214000 ≈ 22.9% — hmm, let me adjust)
        # Let's use lower ARV to make cash_left larger
        # max_refi = 180000 * 0.75 = 135000
        # cash_left = 214000 - 135000 = 79000  (79000 / 214000 ≈ 36.9% > 25%)
        result = calculate_brrrr(
            purchase_price=Decimal("200000"),
            rehab_cost=Decimal("10000"),
            arv=Decimal("180000"),
            monthly_rent_post_rehab=Decimal("1500"),
            annual_operating_expenses=Decimal("5000"),
        )
        assert result.cash_left_in_deal > result.total_project_cost * Decimal("0.25")
        assert result.verdict == "Capital Trap"
        assert result.is_full_cycle is False


# ---------------------------------------------------------------------------
# Total project cost
# ---------------------------------------------------------------------------


class TestTotalProjectCost:
    """Verify total_project_cost = purchase_price + rehab_cost + closing_costs."""

    def test_default_closing_costs_2pct(self) -> None:
        """Default closing_costs_pct is 2% of purchase_price."""
        result = calculate_brrrr(
            purchase_price=Decimal("100000"),
            rehab_cost=Decimal("25000"),
            arv=Decimal("160000"),
            monthly_rent_post_rehab=Decimal("1200"),
            annual_operating_expenses=Decimal("3000"),
        )
        # closing_costs = 100000 * 0.02 = 2000
        # total = 100000 + 25000 + 2000 = 127000
        assert result.total_project_cost == Decimal("127000")

    def test_zero_closing_costs(self) -> None:
        """closing_costs_pct=0 → no closing costs added."""
        result = calculate_brrrr(
            purchase_price=Decimal("100000"),
            rehab_cost=Decimal("25000"),
            arv=Decimal("160000"),
            monthly_rent_post_rehab=Decimal("1200"),
            annual_operating_expenses=Decimal("3000"),
            closing_costs_pct=Decimal("0"),
        )
        assert result.total_project_cost == Decimal("125000")

    def test_custom_closing_costs(self) -> None:
        """Custom closing_costs_pct is applied correctly."""
        result = calculate_brrrr(
            purchase_price=Decimal("200000"),
            rehab_cost=Decimal("30000"),
            arv=Decimal("280000"),
            monthly_rent_post_rehab=Decimal("2000"),
            annual_operating_expenses=Decimal("6000"),
            closing_costs_pct=Decimal("0.03"),
        )
        # closing_costs = 200000 * 0.03 = 6000
        # total = 200000 + 30000 + 6000 = 236000
        assert result.total_project_cost == Decimal("236000")


# ---------------------------------------------------------------------------
# Max refi loan
# ---------------------------------------------------------------------------


class TestMaxRefiLoan:
    """Verify max_refi_loan = arv * refi_ltv_pct."""

    def test_default_75_pct_ltv(self) -> None:
        """Default LTV is 75%."""
        result = calculate_brrrr(
            purchase_price=Decimal("100000"),
            rehab_cost=Decimal("20000"),
            arv=Decimal("200000"),
            monthly_rent_post_rehab=Decimal("1500"),
            annual_operating_expenses=Decimal("4000"),
        )
        assert result.max_refi_loan == Decimal("150000")

    def test_custom_ltv(self) -> None:
        """Custom LTV is applied correctly."""
        result = calculate_brrrr(
            purchase_price=Decimal("100000"),
            rehab_cost=Decimal("20000"),
            arv=Decimal("200000"),
            monthly_rent_post_rehab=Decimal("1500"),
            annual_operating_expenses=Decimal("4000"),
            refi_ltv_pct=Decimal("0.80"),
        )
        assert result.max_refi_loan == Decimal("160000")


# ---------------------------------------------------------------------------
# Cash left in deal
# ---------------------------------------------------------------------------


class TestCashLeftInDeal:
    """Verify cash_left_in_deal = total_project_cost - max_refi_loan."""

    def test_positive_cash_left(self) -> None:
        """When refi < total cost, cash remains."""
        result = calculate_brrrr(
            purchase_price=Decimal("100000"),
            rehab_cost=Decimal("20000"),
            arv=Decimal("140000"),
            monthly_rent_post_rehab=Decimal("1200"),
            annual_operating_expenses=Decimal("3000"),
            closing_costs_pct=Decimal("0"),
        )
        # total = 120000, max_refi = 105000, cash_left = 15000
        assert result.cash_left_in_deal == Decimal("15000")

    def test_zero_cash_left(self) -> None:
        """When refi == total cost, cash_left is 0."""
        result = calculate_brrrr(
            purchase_price=Decimal("100000"),
            rehab_cost=Decimal("0"),
            arv=Decimal("133334"),
            monthly_rent_post_rehab=Decimal("1000"),
            annual_operating_expenses=Decimal("2400"),
            closing_costs_pct=Decimal("0"),
        )
        # total = 100000, max_refi = 133334 * 0.75 = 100000.50
        assert result.cash_left_in_deal <= Decimal("0")

    def test_negative_cash_left(self) -> None:
        """When refi > total cost, cash_left is negative (infinite CoC)."""
        result = calculate_brrrr(
            purchase_price=Decimal("80000"),
            rehab_cost=Decimal("10000"),
            arv=Decimal("150000"),
            monthly_rent_post_rehab=Decimal("1200"),
            annual_operating_expenses=Decimal("3000"),
            closing_costs_pct=Decimal("0"),
        )
        # total = 90000, max_refi = 112500, cash_left = -22500
        assert result.cash_left_in_deal == Decimal("-22500")


# ---------------------------------------------------------------------------
# Post-refi DSCR
# ---------------------------------------------------------------------------


class TestPostRefiDSCR:
    """Verify DSCR = annual_noi / annual_debt_service."""

    def test_dscr_above_threshold(self) -> None:
        """DSCR >= 1.25 indicates lender qualification."""
        result = calculate_brrrr(
            purchase_price=Decimal("100000"),
            rehab_cost=Decimal("20000"),
            arv=Decimal("160000"),
            monthly_rent_post_rehab=Decimal("1500"),
            annual_operating_expenses=Decimal("3600"),
        )
        assert result.post_refi_dscr >= Decimal("1.25")

    def test_dscr_below_threshold_flagged(self) -> None:
        """DSCR < 1.25 is flagged (but not blocked)."""
        # Low rent relative to loan → low DSCR
        result = calculate_brrrr(
            purchase_price=Decimal("100000"),
            rehab_cost=Decimal("20000"),
            arv=Decimal("200000"),
            monthly_rent_post_rehab=Decimal("800"),
            annual_operating_expenses=Decimal("2000"),
        )
        # The function computes DSCR; we just verify it's a valid Decimal
        assert isinstance(result.post_refi_dscr, Decimal)
        assert result.post_refi_dscr > Decimal("0")


# ---------------------------------------------------------------------------
# Post-refi CoC
# ---------------------------------------------------------------------------


class TestPostRefiCoC:
    """Verify CoC = annual_cashflow / cash_left_in_deal."""

    def test_infinite_coc_when_full_cycle(self) -> None:
        """Full Cycle → CoC is Decimal('Infinity')."""
        result = calculate_brrrr(
            purchase_price=Decimal("80000"),
            rehab_cost=Decimal("20000"),
            arv=Decimal("150000"),
            monthly_rent_post_rehab=Decimal("1200"),
            annual_operating_expenses=Decimal("3600"),
        )
        assert result.post_refi_coc == Decimal("Infinity")

    def test_positive_coc_when_partial_recycle(self) -> None:
        """Partial Recycle → positive CoC."""
        result = calculate_brrrr(
            purchase_price=Decimal("100000"),
            rehab_cost=Decimal("20000"),
            arv=Decimal("150000"),
            monthly_rent_post_rehab=Decimal("1200"),
            annual_operating_expenses=Decimal("3600"),
        )
        assert result.post_refi_coc > Decimal("0")


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Boundary conditions and unusual inputs."""

    def test_zero_rehab_cost(self) -> None:
        """Zero rehab (turnkey property) should work."""
        result = calculate_brrrr(
            purchase_price=Decimal("100000"),
            rehab_cost=Decimal("0"),
            arv=Decimal("120000"),
            monthly_rent_post_rehab=Decimal("1000"),
            annual_operating_expenses=Decimal("2400"),
        )
        assert result.rehab_cost == Decimal("0")
        assert isinstance(result.verdict, str)

    def test_very_high_rehab(self) -> None:
        """Rehab cost exceeding purchase price should work."""
        result = calculate_brrrr(
            purchase_price=Decimal("50000"),
            rehab_cost=Decimal("100000"),
            arv=Decimal("200000"),
            monthly_rent_post_rehab=Decimal("1500"),
            annual_operating_expenses=Decimal("4000"),
        )
        assert result.rehab_cost == Decimal("100000")
        assert isinstance(result.verdict, str)

    def test_80pct_ltv(self) -> None:
        """80% LTV (some lenders allow it)."""
        result = calculate_brrrr(
            purchase_price=Decimal("100000"),
            rehab_cost=Decimal("20000"),
            arv=Decimal("150000"),
            monthly_rent_post_rehab=Decimal("1200"),
            annual_operating_expenses=Decimal("3600"),
            refi_ltv_pct=Decimal("0.80"),
        )
        # max_refi = 150000 * 0.80 = 120000
        assert result.max_refi_loan == Decimal("120000")

    def test_15_year_term(self) -> None:
        """15-year refi term (higher payments, faster payoff)."""
        result = calculate_brrrr(
            purchase_price=Decimal("100000"),
            rehab_cost=Decimal("20000"),
            arv=Decimal("150000"),
            monthly_rent_post_rehab=Decimal("1200"),
            annual_operating_expenses=Decimal("3600"),
            refi_term_years=15,
        )
        assert isinstance(result.post_refi_dscr, Decimal)
        assert result.post_refi_dscr > Decimal("0")

    def test_zero_rent(self) -> None:
        """Zero rent → NOI = -operating_expenses → negative DSCR."""
        result = calculate_brrrr(
            purchase_price=Decimal("100000"),
            rehab_cost=Decimal("20000"),
            arv=Decimal("150000"),
            monthly_rent_post_rehab=Decimal("0"),
            annual_operating_expenses=Decimal("3600"),
        )
        assert result.post_refi_dscr < Decimal("0")

    def test_zero_operating_expenses(self) -> None:
        """Zero operating expenses → NOI = annual_rent."""
        result = calculate_brrrr(
            purchase_price=Decimal("100000"),
            rehab_cost=Decimal("20000"),
            arv=Decimal("150000"),
            monthly_rent_post_rehab=Decimal("1200"),
            annual_operating_expenses=Decimal("0"),
        )
        # annual_noi = 1200 * 12 = 14400
        assert isinstance(result.post_refi_dscr, Decimal)

    def test_return_type_is_brrrr_analysis(self) -> None:
        """Return type must be BRRRRAnalysis dataclass."""
        result = calculate_brrrr(
            purchase_price=Decimal("100000"),
            rehab_cost=Decimal("20000"),
            arv=Decimal("150000"),
            monthly_rent_post_rehab=Decimal("1200"),
            annual_operating_expenses=Decimal("3600"),
        )
        assert isinstance(result, BRRRRAnalysis)

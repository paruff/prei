"""Tests for property service layer functions."""

from decimal import Decimal

from core.services.property_service import calculate_noi


class TestCalculateNoi:
    """Tests for calculate_noi in the service layer."""

    def test_positive_noi(self) -> None:
        result = calculate_noi(Decimal("120000"), Decimal("40000"))
        assert result == Decimal("80000.00")

    def test_negative_noi(self) -> None:
        result = calculate_noi(Decimal("30000"), Decimal("45000"))
        assert result == Decimal("-15000.00")

    def test_zero_noi(self) -> None:
        result = calculate_noi(Decimal("50000"), Decimal("50000"))
        assert result == Decimal("0.00")

    def test_decimal_precision(self) -> None:
        result = calculate_noi(Decimal("100000.55"), Decimal("33333.33"))
        assert result == Decimal("66667.22")

    def test_large_values(self) -> None:
        result = calculate_noi(Decimal("999999999.99"), Decimal("1.00"))
        assert result == Decimal("999999998.99")

    def test_zero_income(self) -> None:
        result = calculate_noi(Decimal("0"), Decimal("50000"))
        assert result == Decimal("-50000.00")

    def test_zero_expenses(self) -> None:
        result = calculate_noi(Decimal("75000"), Decimal("0"))
        assert result == Decimal("75000.00")

    def test_all_zero(self) -> None:
        result = calculate_noi(Decimal("0"), Decimal("0"))
        assert result == Decimal("0.00")

    def test_quantized_to_two_places(self) -> None:
        result = calculate_noi(Decimal("100"), Decimal("0.333"))
        assert result == Decimal("99.67")

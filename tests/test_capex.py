"""Tests for CapEx reserve schedule calculations."""

from decimal import Decimal


from core.services.capex import (
    CapExItem,
    CapExItemProtocol,
    calculate_capex_reserve,
    DEFAULT_CAPEX_ITEMS,
)


class TestCapExItem:
    """Tests for CapExItem dataclass."""

    def test_capex_item_creation(self) -> None:
        """Test creating a CapExItem with all required fields."""
        item = CapExItem(
            component_type="roof",
            replacement_cost=Decimal("12000"),
            useful_life_years=25,
            age_years=5,
        )
        assert item.component_type == "roof"
        assert item.replacement_cost == Decimal("12000")
        assert item.useful_life_years == 25
        assert item.age_years == 5

    def test_capex_item_annual_reserve_property(self) -> None:
        """Test that annual_reserve is calculated as replacement_cost / useful_life_years."""
        item = CapExItem(
            component_type="hvac",
            replacement_cost=Decimal("8000"),
            useful_life_years=15,
            age_years=3,
        )
        # 8000 / 15 = 533.33...
        expected = Decimal("8000") / Decimal("15")
        assert item.annual_reserve == expected

    def test_capex_item_needs_replacement_when_past_useful_life(self) -> None:
        """Test that item is flagged when age exceeds useful life."""
        item = CapExItem(
            component_type="water_heater",
            replacement_cost=Decimal("1500"),
            useful_life_years=10,
            age_years=12,
        )
        assert item.needs_replacement is True

    def test_capex_item_not_needs_replacement_when_within_life(self) -> None:
        """Test that item is not flagged when age is within useful life."""
        item = CapExItem(
            component_type="appliances",
            replacement_cost=Decimal("3000"),
            useful_life_years=7,
            age_years=3,
        )
        assert item.needs_replacement is False

    def test_capex_item_edge_case_age_equals_useful_life(self) -> None:
        """Test that item needs replacement when age equals useful life."""
        item = CapExItem(
            component_type="roof",
            replacement_cost=Decimal("12000"),
            useful_life_years=25,
            age_years=25,
        )
        assert item.needs_replacement is True


class TestCalculateCapExReserve:
    """Tests for calculate_capex_reserve function."""

    def test_monthly_reserve_sum_of_annual_reserves_divided_by_12(self) -> None:
        """Test total monthly reserve = sum of all annual reserves / 12."""
        items: list[CapExItemProtocol] = [
            CapExItem("roof", Decimal("12000"), 25, 5),  # 480/yr
            CapExItem("hvac", Decimal("8000"), 15, 3),  # 533.33/yr
            CapExItem("water_heater", Decimal("1500"), 10, 2),  # 150/yr
            CapExItem("appliances", Decimal("3000"), 7, 1),  # 428.57/yr
        ]
        # Sum = 480 + 533.33 + 150 + 428.57 = 1591.90 / 12 = 132.66/mo
        monthly = calculate_capex_reserve(items)
        expected_annual = (
            Decimal("12000") / Decimal("25")
            + Decimal("8000") / Decimal("15")
            + Decimal("1500") / Decimal("10")
            + Decimal("3000") / Decimal("7")
        )
        expected_monthly = (expected_annual / Decimal("12")).quantize(Decimal("0.01"))
        assert monthly == expected_monthly

    def test_empty_list_returns_zero(self) -> None:
        """Test that empty items list returns zero reserve."""
        monthly = calculate_capex_reserve([])
        assert monthly == Decimal("0")

    def test_single_item_monthly_reserve(self) -> None:
        """Test monthly reserve with single item."""
        items: list[CapExItemProtocol] = [CapExItem("roof", Decimal("12000"), 25, 5)]
        monthly = calculate_capex_reserve(items)
        # 12000 / 25 = 480/yr, /12 = 40/mo
        assert monthly == Decimal("40.00")

    def test_returns_decimal_with_two_places(self) -> None:
        """Test that result is quantized to 2 decimal places."""
        items: list[CapExItemProtocol] = [CapExItem("hvac", Decimal("8000"), 15, 3)]
        monthly = calculate_capex_reserve(items)
        assert monthly == monthly.quantize(Decimal("0.01"))
        # 8000/15 = 533.333..., /12 = 44.444..., quantized = 44.44
        assert monthly == Decimal("44.44")


class TestDefaultCapExItems:
    """Tests for default CapEx items based on property age."""

    def test_default_items_exist(self) -> None:
        """Test that DEFAULT_CAPEX_ITEMS has 4 standard components."""
        assert len(DEFAULT_CAPEX_ITEMS) == 4
        types = {item.component_type for item in DEFAULT_CAPEX_ITEMS}
        assert types == {"roof", "hvac", "water_heater", "appliances"}

    def test_default_roof_values(self) -> None:
        """Test default roof: 25yr, $12K."""
        roof = next(i for i in DEFAULT_CAPEX_ITEMS if i.component_type == "roof")
        assert roof.useful_life_years == 25
        assert roof.replacement_cost == Decimal("12000")

    def test_default_hvac_values(self) -> None:
        """Test default HVAC: 15yr, $8K."""
        hvac = next(i for i in DEFAULT_CAPEX_ITEMS if i.component_type == "hvac")
        assert hvac.useful_life_years == 15
        assert hvac.replacement_cost == Decimal("8000")

    def test_default_water_heater_values(self) -> None:
        """Test default water heater: 10yr, $1.5K."""
        wh = next(i for i in DEFAULT_CAPEX_ITEMS if i.component_type == "water_heater")
        assert wh.useful_life_years == 10
        assert wh.replacement_cost == Decimal("1500")

    def test_default_appliances_values(self) -> None:
        """Test default appliances: 7yr, $3K."""
        app = next(i for i in DEFAULT_CAPEX_ITEMS if i.component_type == "appliances")
        assert app.useful_life_years == 7
        assert app.replacement_cost == Decimal("3000")

    def test_default_items_have_zero_age(self) -> None:
        """Test that default items start with age_years = 0."""
        for item in DEFAULT_CAPEX_ITEMS:
            assert item.age_years == 0

    def test_get_defaults_for_property_age_adjusts_age(self) -> None:
        """Test that getting defaults for a property age sets age_years."""
        from core.services.capex import get_default_capex_items_for_age

        items = get_default_capex_items_for_age(10)
        for item in items:
            assert item.age_years == 10


class TestCapExIntegrationWithNOI:
    """Tests for CapEx reserve integration with NOI calculation."""

    def test_noi_with_capex_param(self) -> None:
        """Test that noi() accepts optional capex_reserve parameter."""
        from investor_app.finance.utils import noi

        monthly_income = Decimal("2500")
        monthly_expenses = Decimal("1000")
        capex_reserve = Decimal("200")

        # NOI = (income - expenses - capex) * 12
        result = noi(monthly_income, monthly_expenses, capex_reserve)
        expected = (monthly_income - monthly_expenses - capex_reserve) * Decimal("12")
        assert result == expected

    def test_noi_without_capex_works_as_before(self) -> None:
        """Test that noi() still works without capex parameter (backward compat)."""
        from investor_app.finance.utils import noi

        monthly_income = Decimal("2500")
        monthly_expenses = Decimal("1000")

        result = noi(monthly_income, monthly_expenses)
        expected = (monthly_income - monthly_expenses) * Decimal("12")
        assert result == expected

    def test_noi_with_zero_capex(self) -> None:
        """Test that noi() with capex=0 works same as without."""
        from investor_app.finance.utils import noi

        monthly_income = Decimal("2500")
        monthly_expenses = Decimal("1000")

        result_with = noi(monthly_income, monthly_expenses, Decimal("0"))
        result_without = noi(monthly_income, monthly_expenses)
        assert result_with == result_without

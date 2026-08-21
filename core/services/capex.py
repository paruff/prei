"""CapEx reserve schedule calculations for major property components."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import List, Protocol

from core.models import Property


class CapExItemProtocol(Protocol):
    """Protocol for objects that can be used as CapEx items.

    Both the dataclass CapExItem and the Django model CapExItem implement this.
    """

    component_type: str
    replacement_cost: Decimal
    useful_life_years: int
    age_years: int

    @property
    def annual_reserve(self) -> Decimal: ...

    @property
    def needs_replacement(self) -> bool: ...

    @property
    def remaining_life_years(self) -> int: ...


@dataclass
class CapExItem:
    """A single CapEx component with its reserve calculation.

    Attributes:
        component_type: Type of component (roof, hvac, water_heater, appliances).
        replacement_cost: Estimated cost to replace the component.
        useful_life_years: Expected useful life in years.
        age_years: Current age of the component in years.
    """

    component_type: str
    replacement_cost: Decimal
    useful_life_years: int
    age_years: int = 0

    @property
    def annual_reserve(self) -> Decimal:
        """Annual reserve = replacement_cost / useful_life_years."""
        return self.replacement_cost / Decimal(self.useful_life_years)

    @property
    def needs_replacement(self) -> bool:
        """True if component age exceeds or equals useful life."""
        return self.age_years >= self.useful_life_years

    @property
    def remaining_life_years(self) -> int:
        """Remaining useful life in years (can be negative)."""
        return self.useful_life_years - self.age_years


# Default CapEx items per spec
DEFAULT_CAPEX_ITEMS: List[CapExItem] = [
    CapExItem("roof", Decimal("12000"), 25, 0),
    CapExItem("hvac", Decimal("8000"), 15, 0),
    CapExItem("water_heater", Decimal("1500"), 10, 0),
    CapExItem("appliances", Decimal("3000"), 7, 0),
]


def get_default_capex_items_for_age(property_age_years: int) -> List[CapExItem]:
    """Get default CapEx items adjusted for property age.

    Args:
        property_age_years: Age of the property in years.

    Returns:
        List of CapExItem with age_years set to property_age_years.
    """
    return [
        CapExItem(
            component_type=item.component_type,
            replacement_cost=item.replacement_cost,
            useful_life_years=item.useful_life_years,
            age_years=property_age_years,
        )
        for item in DEFAULT_CAPEX_ITEMS
    ]


def calculate_capex_reserve(items: List[CapExItemProtocol]) -> Decimal:
    """Calculate total monthly CapEx reserve from a list of items.

    Total monthly reserve = sum(item.annual_reserve for item in items) / 12

    Args:
        items: List of objects implementing CapExItemProtocol.

    Returns:
        Monthly reserve amount quantized to 2 decimal places.
    """
    if not items:
        return Decimal("0")

    total_annual = sum((item.annual_reserve for item in items), Decimal("0"))
    monthly = total_annual / Decimal("12")
    return monthly.quantize(Decimal("0.01"))


def calculate_capex_reserve_for_property(property: Property) -> Decimal:
    """Calculate CapEx reserve for a property using its CapEx items.

    Args:
        property: Property instance with related capex_items.

    Returns:
        Monthly reserve amount.
    """
    items: List[CapExItemProtocol] = list(property.capex_items.all())
    if not items:
        # Fall back to defaults based on property age if available
        property_age = 0
        if property.purchase_date:
            from django.utils import timezone

            property_age = (timezone.now().date() - property.purchase_date).days // 365
        items = get_default_capex_items_for_age(property_age)  # type: ignore[assignment]
    return calculate_capex_reserve(items)

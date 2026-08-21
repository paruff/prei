"""Pytest configuration for finance utility tests."""

import pytest
from decimal import Decimal
from typing import TYPE_CHECKING

from django.contrib.auth import get_user_model
from core.models import Property

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser
    User = AbstractUser
else:
    User = get_user_model()


@pytest.fixture
def user(db) -> User:
    """Create a test user."""
    return User.objects.create_user(username="testuser", password="testpass123")


@pytest.fixture
def property_obj(db, user) -> Property:
    """Create a test property with typical values."""
    return Property.objects.create(
        user=user,
        address="123 Test St",
        city="Test City",
        state="TS",
        zip_code="12345",
        purchase_price=Decimal("300000"),
        purchase_date="2023-01-01",
        monthly_rent_gross=Decimal("2500"),
        other_monthly_income=Decimal("100"),
        property_taxes_annual=Decimal("3600"),
        insurance_annual=Decimal("1200"),
        hoa_monthly=Decimal("0"),
        maintenance_monthly=Decimal("150"),
        capex_monthly=Decimal("100"),
        vacancy_rate=Decimal("0.08"),
        mgmt_fee_pct=Decimal("0.10"),
        down_payment_pct=Decimal("0.20"),
        interest_rate=Decimal("0.07"),
        loan_term_years=30,
    )

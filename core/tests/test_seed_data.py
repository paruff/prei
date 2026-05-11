from __future__ import annotations

from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from core.management.commands.seed_data import DEMO_EMAIL, DEMO_PASSWORD
from core.models import InvestmentAnalysis, OperatingExpense, Property, RentalIncome


@pytest.mark.django_db
class TestSeedDataCommand:
    def test_seed_data_creates_demo_user_and_records(self) -> None:
        out = StringIO()
        call_command("seed_data", stdout=out)

        user = get_user_model().objects.get(email=DEMO_EMAIL)
        assert user.is_superuser is True
        assert user.is_staff is True
        assert user.check_password(DEMO_PASSWORD) is True

        properties = Property.objects.filter(user=user)
        assert properties.count() == 3
        assert RentalIncome.objects.filter(property__user=user).count() == 4
        assert OperatingExpense.objects.filter(property__user=user).count() == 12
        assert InvestmentAnalysis.objects.filter(property__user=user).count() == 3

        for prop in properties:
            assert prop.operating_expenses.count() >= 4
            assert prop.analysis.noi is not None
            assert prop.analysis.cap_rate is not None

        output = out.getvalue()
        assert "Demo credentials" in output
        assert "Summary (address | NOI | cap rate)" in output

    def test_seed_data_is_idempotent_without_reset(self) -> None:
        call_command("seed_data")
        first_counts = (
            Property.objects.count(),
            RentalIncome.objects.count(),
            OperatingExpense.objects.count(),
            InvestmentAnalysis.objects.count(),
        )

        call_command("seed_data")
        second_counts = (
            Property.objects.count(),
            RentalIncome.objects.count(),
            OperatingExpense.objects.count(),
            InvestmentAnalysis.objects.count(),
        )

        assert second_counts == first_counts

    def test_seed_data_reset_recreates_seed_for_demo_user(self) -> None:
        call_command("seed_data")
        user = get_user_model().objects.get(email=DEMO_EMAIL)
        Property.objects.create(
            user=user,
            address="999 Demo Reset St",
            city="Austin",
            state="TX",
            zip_code="78701",
            purchase_price="100000.00",
        )
        assert Property.objects.filter(user=user).count() == 4

        call_command("seed_data", "--reset")
        assert Property.objects.filter(user=user).count() == 3
        assert RentalIncome.objects.filter(property__user=user).count() == 4
        assert OperatingExpense.objects.filter(property__user=user).count() == 12
        assert InvestmentAnalysis.objects.filter(property__user=user).count() == 3

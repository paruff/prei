from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest
from django.core.management import CommandError, call_command

from core.management.commands.import_csv import Command
from core.models import OperatingExpense, Property, RentalIncome

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
PROPERTIES_CSV = DATA_DIR / "properties.csv"
RENTS_CSV = DATA_DIR / "rents.csv"
EXPENSES_CSV = DATA_DIR / "expenses.csv"


def command_has_update_flag() -> bool:
    parser = Command().create_parser("manage.py", "import_csv")
    return any("--update" in action.option_strings for action in parser._actions)


@pytest.mark.django_db
class TestImportCSVCommand:
    def test_import_creates_properties(self, user) -> None:
        call_command(
            "import_csv",
            user.email,
            str(PROPERTIES_CSV),
            str(RENTS_CSV),
            str(EXPENSES_CSV),
        )

        assert Property.objects.count() == 2
        assert Property.objects.filter(address="123 Main St").exists()

    def test_import_creates_rental_income(self, user) -> None:
        call_command(
            "import_csv",
            user.email,
            str(PROPERTIES_CSV),
            str(RENTS_CSV),
            str(EXPENSES_CSV),
        )

        assert RentalIncome.objects.count() == 2
        assert RentalIncome.objects.filter(monthly_rent=Decimal("2000")).exists()

    def test_import_creates_expenses(self, user) -> None:
        call_command(
            "import_csv",
            user.email,
            str(PROPERTIES_CSV),
            str(RENTS_CSV),
            str(EXPENSES_CSV),
        )

        assert OperatingExpense.objects.count() == 3
        assert OperatingExpense.objects.filter(category="Insurance").exists()

    def test_import_with_update_flag_is_idempotent(self, user) -> None:
        if not command_has_update_flag():
            pytest.skip("import_csv command does not support --update idempotent mode")

        call_command(
            "import_csv",
            user.email,
            str(PROPERTIES_CSV),
            str(RENTS_CSV),
            str(EXPENSES_CSV),
            "--update",
        )
        first_counts = (
            Property.objects.count(),
            RentalIncome.objects.count(),
            OperatingExpense.objects.count(),
        )

        call_command(
            "import_csv",
            user.email,
            str(PROPERTIES_CSV),
            str(RENTS_CSV),
            str(EXPENSES_CSV),
            "--update",
        )
        second_counts = (
            Property.objects.count(),
            RentalIncome.objects.count(),
            OperatingExpense.objects.count(),
        )

        assert second_counts == first_counts

    @pytest.mark.parametrize(
        ("invalid_target", "csv_content", "error_message"),
        [
            (
                "properties",
                "city,state,zip_code,purchase_price,purchase_date,sqft,units,notes\n"
                "Town,CA,90000,120000,2025-01-01,1500,1,Missing address\n",
                "Properties CSV missing required column: address",
            ),
            (
                "rents",
                "monthly_rent,effective_date,vacancy_rate\n2000,2025-03-01,0.05\n",
                "Rents CSV missing required column: property_id",
            ),
            (
                "expenses",
                "category,amount,frequency,effective_date\nTax,300,monthly,2025-03-01\n",
                "Expenses CSV missing required column: property_id",
            ),
        ],
    )
    def test_import_invalid_csv_raises_error(
        self,
        user,
        tmp_path: Path,
        invalid_target: str,
        csv_content: str,
        error_message: str,
    ) -> None:
        invalid_csv = tmp_path / f"invalid_{invalid_target}.csv"
        invalid_csv.write_text(csv_content, encoding="utf-8")

        properties_csv = str(PROPERTIES_CSV)
        rents_csv = str(RENTS_CSV)
        expenses_csv = str(EXPENSES_CSV)
        if invalid_target == "properties":
            properties_csv = str(invalid_csv)
        elif invalid_target == "rents":
            rents_csv = str(invalid_csv)
        elif invalid_target == "expenses":
            expenses_csv = str(invalid_csv)

        with pytest.raises(CommandError, match=error_message):
            call_command(
                "import_csv",
                user.email,
                properties_csv,
                rents_csv,
                expenses_csv,
            )

    def test_import_nonexistent_file_raises_error(self, user, tmp_path: Path) -> None:
        missing_csv = tmp_path / "missing_properties.csv"

        with pytest.raises(CommandError, match="Properties CSV not found"):
            call_command("import_csv", user.email, str(missing_csv))

    def test_property_fields_match_csv(self, user) -> None:
        call_command(
            "import_csv",
            user.email,
            str(PROPERTIES_CSV),
            str(RENTS_CSV),
            str(EXPENSES_CSV),
        )

        property_obj = Property.objects.get(address="123 Main St")
        rental_obj = RentalIncome.objects.get(property__address="123 Main St")
        expense_obj = OperatingExpense.objects.get(
            property__address="123 Main St", category="Tax"
        )
        assert isinstance(property_obj.purchase_price, Decimal)
        assert property_obj.purchase_price == Decimal("120000")
        assert isinstance(rental_obj.monthly_rent, Decimal)
        assert rental_obj.monthly_rent == Decimal("2000")
        assert isinstance(expense_obj.amount, Decimal)
        assert expense_obj.amount == Decimal("300")

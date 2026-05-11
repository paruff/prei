from __future__ import annotations

import argparse
from datetime import date
from decimal import Decimal

from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from core.models import OperatingExpense, Property, RentalIncome
from investor_app.finance.utils import compute_analysis_for_property

DEMO_EMAIL = "demo@prei.dev"
DEMO_PASSWORD = "DemoPass123!"
DEMO_USERNAME = "demo"

SEED_PROPERTIES = (
    {
        "address": "4127 South Congress Ave",
        "city": "Austin",
        "state": "TX",
        "zip_code": "78745",
        "purchase_price": Decimal("325000.00"),
        "purchase_date": date(2024, 1, 15),
        "sqft": 1800,
        "units": 1,
        "notes": "Seed demo property: SFR",
        "rents": [Decimal("2400.00")],
        "expenses": (
            ("Property Tax", Decimal("410.00"), OperatingExpense.Frequency.MONTHLY),
            ("Insurance", Decimal("145.00"), OperatingExpense.Frequency.MONTHLY),
            ("Maintenance", Decimal("180.00"), OperatingExpense.Frequency.MONTHLY),
            (
                "Property Management",
                Decimal("192.00"),
                OperatingExpense.Frequency.MONTHLY,
            ),
        ),
    },
    {
        "address": "1482 Poplar Ave",
        "city": "Memphis",
        "state": "TN",
        "zip_code": "38104",
        "purchase_price": Decimal("198000.00"),
        "purchase_date": date(2023, 10, 20),
        "sqft": 2200,
        "units": 2,
        "notes": "Seed demo property: Duplex",
        "rents": [Decimal("1100.00"), Decimal("1100.00")],
        "expenses": (
            ("Property Tax", Decimal("255.00"), OperatingExpense.Frequency.MONTHLY),
            ("Insurance", Decimal("115.00"), OperatingExpense.Frequency.MONTHLY),
            ("Maintenance", Decimal("175.00"), OperatingExpense.Frequency.MONTHLY),
            (
                "Property Management",
                Decimal("176.00"),
                OperatingExpense.Frequency.MONTHLY,
            ),
        ),
    },
    {
        "address": "9064 Gratiot Ave",
        "city": "Detroit",
        "state": "MI",
        "zip_code": "48213",
        "purchase_price": Decimal("62500.00"),
        "purchase_date": date(2024, 3, 1),
        "sqft": 1100,
        "units": 1,
        "notes": "Seed demo property: Distressed SFR (post-rehab)",
        "rents": [Decimal("950.00")],
        "expenses": (
            ("Property Tax", Decimal("95.00"), OperatingExpense.Frequency.MONTHLY),
            ("Insurance", Decimal("85.00"), OperatingExpense.Frequency.MONTHLY),
            ("Maintenance", Decimal("120.00"), OperatingExpense.Frequency.MONTHLY),
            (
                "Property Management",
                Decimal("76.00"),
                OperatingExpense.Frequency.MONTHLY,
            ),
        ),
    },
)


class Command(BaseCommand):
    help = "Seed demo user and sample properties with rental, expenses, and analyses"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing demo user properties before seeding",
        )

    def handle(self, *args, **options) -> None:
        demo_user = self._get_or_create_demo_user()

        self.stdout.write(self.style.SUCCESS("Demo credentials"))
        self.stdout.write(f"  email: {DEMO_EMAIL}")
        self.stdout.write(f"  password: {DEMO_PASSWORD}")

        if options["reset"]:
            deleted_count, _ = Property.objects.filter(user=demo_user).delete()
            self.stdout.write(
                self.style.WARNING(
                    f"--reset enabled: deleted existing demo-owned records={deleted_count}"
                )
            )

        summary_rows: list[tuple[str, Decimal, Decimal]] = []
        created_count = 0
        skipped_count = 0

        for seed in SEED_PROPERTIES:
            prop, created = Property.objects.get_or_create(
                user=demo_user,
                address=seed["address"],
                city=seed["city"],
                state=seed["state"],
                zip_code=seed["zip_code"],
                defaults={
                    "purchase_price": seed["purchase_price"],
                    "purchase_date": seed["purchase_date"],
                    "sqft": seed["sqft"],
                    "units": seed["units"],
                    "notes": seed["notes"],
                },
            )

            if created:
                created_count += 1
                for monthly_rent in seed["rents"]:
                    RentalIncome.objects.create(
                        property=prop,
                        monthly_rent=monthly_rent,
                        effective_date=seed["purchase_date"],
                    )
                for category, amount, frequency in seed["expenses"]:
                    OperatingExpense.objects.create(
                        property=prop,
                        category=category,
                        amount=amount,
                        frequency=frequency,
                        effective_date=seed["purchase_date"],
                    )
                self.stdout.write(self.style.SUCCESS(f"Created: {prop.address}"))
            else:
                skipped_count += 1
                self.stdout.write(
                    self.style.WARNING(f"Skipped existing: {prop.address}")
                )

            analysis = compute_analysis_for_property(prop)
            summary_rows.append((prop.address, analysis.noi, analysis.cap_rate))

        self.stdout.write("")
        self.stdout.write("Summary (address | NOI | cap rate)")
        for address, noi, cap_rate in summary_rows:
            self.stdout.write(f"- {address} | {noi} | {cap_rate}")
        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"seed_data complete. created={created_count} skipped={skipped_count}"
            )
        )

    def _get_or_create_demo_user(self) -> AbstractBaseUser:
        User = get_user_model()
        user = User.objects.filter(email=DEMO_EMAIL).first()
        if user is not None:
            return user

        if hasattr(User, "username"):
            base_username = DEMO_USERNAME
            username = base_username
            suffix = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{suffix}"
                suffix += 1
            return User.objects.create_superuser(
                username=username,
                email=DEMO_EMAIL,
                password=DEMO_PASSWORD,
            )

        return User.objects.create_superuser(email=DEMO_EMAIL, password=DEMO_PASSWORD)

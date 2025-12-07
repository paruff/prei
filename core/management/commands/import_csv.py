from __future__ import annotations

import csv
from decimal import Decimal
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from core.models import Property, RentalIncome, OperatingExpense


class Command(BaseCommand):
    help = "Import properties, rental incomes, and operating expenses from CSV files"

    def add_arguments(self, parser):
        parser.add_argument("user_email", help="Email of the user to own imported properties")
        parser.add_argument("properties_csv", type=str, help="Path to properties CSV")
        parser.add_argument("rents_csv", type=str, nargs="?", default=None, help="Path to rental incomes CSV")
        parser.add_argument("expenses_csv", type=str, nargs="?", default=None, help="Path to operating expenses CSV")

    def handle(self, *args, **options):
        User = get_user_model()
        email = options["user_email"]
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise CommandError(f"User with email {email} does not exist. Create the user first.")

        properties_path = Path(options["properties_csv"]).expanduser()
        rents_path = Path(options["rents_csv"]).expanduser() if options["rents_csv"] else None
        expenses_path = Path(options["expenses_csv"]).expanduser() if options["expenses_csv"] else None

        if not properties_path.exists():
            raise CommandError(f"Properties CSV not found: {properties_path}")

        created_count = 0
        with properties_path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                prop = Property.objects.create(
                    user=user,
                    address=row["address"],
                    city=row.get("city", ""),
                    state=row.get("state", ""),
                    zip_code=row.get("zip_code", ""),
                    purchase_price=Decimal(row.get("purchase_price", "0")),
                    purchase_date=row.get("purchase_date") or None,
                    sqft=int(row.get("sqft") or 0) or None,
                    units=int(row.get("units") or 1),
                    notes=row.get("notes", ""),
                )
                created_count += 1

        self.stdout.write(self.style.SUCCESS(f"Imported {created_count} properties."))

        if rents_path and rents_path.exists():
            rents_created = 0
            with rents_path.open(newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        prop = Property.objects.get(id=int(row["property_id"]))
                    except Property.DoesNotExist:
                        self.stdout.write(self.style.WARNING(f"Skipping rent: property_id {row['property_id']} not found"))
                        continue
                    RentalIncome.objects.create(
                        property=prop,
                        monthly_rent=Decimal(row.get("monthly_rent", "0")),
                        effective_date=row.get("effective_date"),
                        vacancy_rate=Decimal(row.get("vacancy_rate", "0.05")),
                    )
                    rents_created += 1
            self.stdout.write(self.style.SUCCESS(f"Imported {rents_created} rental incomes."))

        if expenses_path and expenses_path.exists():
            expenses_created = 0
            with expenses_path.open(newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        prop = Property.objects.get(id=int(row["property_id"]))
                    except Property.DoesNotExist:
                        self.stdout.write(self.style.WARNING(f"Skipping expense: property_id {row['property_id']} not found"))
                        continue
                    OperatingExpense.objects.create(
                        property=prop,
                        category=row.get("category", "Other"),
                        amount=Decimal(row.get("amount", "0")),
                        frequency=row.get("frequency", OperatingExpense.Frequency.MONTHLY),
                        effective_date=row.get("effective_date"),
                    )
                    expenses_created += 1
            self.stdout.write(self.style.SUCCESS(f"Imported {expenses_created} operating expenses."))

from decimal import Decimal
from django.core.management.base import BaseCommand

from core.models import MarketSnapshot


class Command(BaseCommand):
    help = "Seed MarketSnapshot with a few sample entries for demo purposes"

    def handle(self, *args, **options):
        samples = [
            dict(area_type="zip", zip_code="78701", state="TX", rent_index=Decimal("1800"), price_trend=Decimal("0.14"), crime_score=Decimal("2.3"), school_rating=Decimal("8.4")),
            dict(area_type="zip", zip_code="80203", state="CO", rent_index=Decimal("1600"), price_trend=Decimal("0.10"), crime_score=Decimal("2.9"), school_rating=Decimal("8.0")),
            dict(area_type="zip", zip_code="94110", state="CA", rent_index=Decimal("2500"), price_trend=Decimal("0.08"), crime_score=Decimal("3.6"), school_rating=Decimal("7.2")),
        ]
        created = 0
        for s in samples:
            obj, was_created = MarketSnapshot.objects.update_or_create(
                zip_code=s.get("zip_code"), state=s.get("state"), defaults=s
            )
            created += 1 if was_created else 0
        self.stdout.write(self.style.SUCCESS(f"Seeded market snapshots. created={created}"))

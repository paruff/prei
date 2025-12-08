from typing import Dict, Iterable

from django.core.management.base import BaseCommand
from django.db import transaction

from core.integrations.sources import dummy_adapter
from core.models import Listing


class Command(BaseCommand):
    help = "Fetch listings from configured sources and upsert into the Listing model"

    def handle(self, *args, **options):
        count_created = 0
        count_updated = 0

        # In Phase 1, we only use a dummy adapter. Later, iterate multiple sources.
        records: Iterable[Dict] = dummy_adapter.fetch()

        with transaction.atomic():
            for data in records:
                obj, created = Listing.objects.update_or_create(
                    url=data["url"],
                    defaults={
                        "source": data["source"],
                        "address": data["address"],
                        "city": data.get("city", ""),
                        "state": data.get("state", ""),
                        "zip_code": data.get("zip_code", ""),
                        "price": data["price"],
                        "beds": data.get("beds", 0),
                        "baths": data.get("baths", 0),
                        "sq_ft": data.get("sq_ft", 0),
                        "property_type": data.get("property_type", ""),
                        "posted_at": data["posted_at"],
                    },
                )
                if created:
                    count_created += 1
                else:
                    count_updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Listings fetch complete. created={count_created} updated={count_updated}"
            )
        )

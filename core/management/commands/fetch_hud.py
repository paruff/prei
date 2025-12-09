from django.core.management.base import BaseCommand
from core.integrations.hud_adapter import fetch_properties, is_enabled
from core.models import Listing
from decimal import Decimal


class Command(BaseCommand):
    help = "Fetch HUD properties for a given state/zip and upsert into Listing"

    def add_arguments(self, parser):
        parser.add_argument("--state", type=str, default="", help="State code, e.g., TX")
        parser.add_argument("--zip", type=str, default="", help="ZIP code, e.g., 78701")

    def handle(self, *args, **options):
        if not is_enabled():
            self.stdout.write(self.style.WARNING("HUD integration disabled. Set HUD_ENABLED=true to enable."))
            return

        state = options.get("state") or None
        zip_code = options.get("zip") or None
        props = fetch_properties(state=state, zip_code=zip_code)
        created, updated = 0, 0
        for p in props:
            obj, was_created = Listing.objects.update_or_create(
                url=p["url"],
                defaults={
                    "address": p.get("address", ""),
                    "city": p.get("city", ""),
                    "state": p.get("state", ""),
                    "zip_code": p.get("zip_code", ""),
                    "price": Decimal(str(p.get("price", 0))),
                    "beds": p.get("beds", 0),
                    "baths": p.get("baths", 0),
                    "sq_ft": p.get("sq_ft", 0),
                },
            )
            created += 1 if was_created else 0
            updated += 0 if was_created else 1
        self.stdout.write(self.style.SUCCESS(f"HUD fetch complete. Created={created} Updated={updated}"))

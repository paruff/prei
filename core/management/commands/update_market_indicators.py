"""Management command to update market indicators from external data sources."""

from django.core.management.base import BaseCommand

from core.integrations.market.market_trends import update_market_indicators


class Command(BaseCommand):
    """Update market indicators from external data sources.

    Usage:
        python manage.py update_market_indicators [--metro METRO_AREA]

    Examples:
        python manage.py update_market_indicators
        python manage.py update_market_indicators --metro "Dallas-Fort Worth-Arlington, TX"
    """

    help = "Update market cycle indicators from external data sources"

    def add_arguments(self, parser):
        parser.add_argument(
            "--metro",
            type=str,
            help="Specific metro area to update (e.g., 'Dallas-Fort Worth-Arlington, TX'). If not provided, updates all tracked metros.",
        )

    def handle(self, *args, **options):
        metro: str = options.get("metro") or ""
        if metro:
            self.stdout.write(f"Updating market indicators for {metro}...")
        else:
            self.stdout.write("Updating market indicators for all tracked metros...")

        result = update_market_indicators(metro)

        self.stdout.write(
            self.style.SUCCESS(
                f"Updated market indicators: {result['created']} created, "
                f"{result['updated']} updated, {result['errors']} errors"
            )
        )
        self.stdout.write(f"Metro areas processed: {', '.join(result['metro_areas'])}")

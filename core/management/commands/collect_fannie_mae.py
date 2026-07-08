"""Management command to collect Fannie Mae HomePath REO listings."""

from __future__ import annotations

import hashlib
import logging
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from core.integrations.sources.fannie_mae import FannieMaeHomePathClient
from core.models import DiscoveryRequest, PipelineProperty

logger = logging.getLogger("prei.scraper.fannie_mae")


class Command(BaseCommand):
    """Fetch Fannie Mae HomePath listings and upsert into pipeline."""

    help = "Collect Fannie Mae HomePath REO listings for target locations"

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--location",
            type=str,
            help="City, State or ZIP code to search",
        )
        parser.add_argument(
            "--request-id",
            type=int,
            help="Fulfill a specific DiscoveryRequest by ID",
        )
        parser.add_argument(
            "--all-pending",
            action="store_true",
            help="Fulfill all pending DiscoveryRequests for Fannie Mae",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        # Resolve target location(s)
        targets = self._resolve_targets(options)

        if not targets:
            self.stdout.write(self.style.WARNING("No targets to process."))
            return

        client = FannieMaeHomePathClient()

        for location, request in targets:
            self._process_location(client, location, request)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _resolve_targets(
        self, options: dict[str, Any]
    ) -> list[tuple[str, DiscoveryRequest | None]]:
        """Determine the list of (location, request_or_None) to process."""
        targets: list[tuple[str, DiscoveryRequest | None]] = []

        if options.get("location"):
            targets.append((str(options["location"]).strip(), None))

        if options.get("request_id"):
            try:
                req = DiscoveryRequest.objects.get(id=options["request_id"])
                if req.source.source_type != "fannie":
                    raise CommandError(
                        f"DiscoveryRequest {req.id} is for source "
                        f"'{req.source.source_type}', not 'fannie'."
                    )
                targets.append((req.location, req))
            except DiscoveryRequest.DoesNotExist:
                raise CommandError(
                    f"DiscoveryRequest with id={options['request_id']} not found."
                )

        if options.get("all_pending"):
            pending = DiscoveryRequest.objects.filter(
                source__source_type="fannie",
                status=DiscoveryRequest.Status.REQUESTED,
            )
            for req in pending:
                targets.append((req.location, req))

        return targets

    def _process_location(
        self,
        client: FannieMaeHomePathClient,
        location: str,
        request: DiscoveryRequest | None,
    ) -> None:
        """Fetch listings for one location and upsert into PipelineProperty."""
        self.stdout.write(f"Searching Fannie Mae HomePath: {location} ...")

        listings = client.search_by_location(location)

        if not listings:
            self.stdout.write(
                self.style.WARNING(
                    f"No listings found for {location} (site may be blocked by WAF)."
                )
            )
            if request:
                request.status = DiscoveryRequest.Status.COMPLETED
                request.properties_found = 0
                request.completed_at = timezone.now()
                request.save(
                    update_fields=["status", "properties_found", "completed_at"]
                )
            return

        now = timezone.now()
        new_count = 0
        dup_count = 0

        with transaction.atomic():
            # Resolve user: use the DiscoveryRequest owner if available,
            # otherwise the first superuser as a fallback
            user = request.user if request else self._get_default_user()

            for listing in listings:
                address_hash = self._compute_address_hash(
                    listing.get("address", ""),
                    listing.get("city", ""),
                    listing.get("state", ""),
                )

                defaults = {
                    "user": user,
                    "source_type": PipelineProperty.SourceType.FANNIE,
                    "source_id": address_hash,
                    "address": listing.get("address", ""),
                    "address_hash": address_hash,
                    "stage": PipelineProperty.Stage.DISCOVERED,
                    "status": PipelineProperty.Status.ACTIVE,
                    "price": listing.get("price"),
                    "beds": listing.get("beds"),
                    "baths": listing.get("baths"),
                    "sqft": listing.get("sq_ft"),
                    "discovered_at": now,
                }

                _, created = PipelineProperty.objects.update_or_create(
                    user=user,
                    source_type=PipelineProperty.SourceType.FANNIE,
                    source_id=address_hash,
                    defaults=defaults,
                )

                if created:
                    new_count += 1
                else:
                    dup_count += 1

        # Update the request
        if request:
            request.status = DiscoveryRequest.Status.COMPLETED
            request.properties_found = new_count
            request.completed_at = now
            request.save(update_fields=["status", "properties_found", "completed_at"])

        self.stdout.write(
            self.style.SUCCESS(
                f"{location}: {new_count} new, {dup_count} duplicates skipped."
            )
        )
        logger.info(
            "Fannie Mae %s: %d new, %d duplicates",
            location,
            new_count,
            dup_count,
        )

    @staticmethod
    def _compute_address_hash(address: str, city: str, state: str) -> str:
        """SHA-256 hash of normalized address for dedup."""
        normalized = (
            f"{address.strip().lower()}|{city.strip().lower()}|{state.strip().lower()}"
        )
        return hashlib.sha256(normalized.encode()).hexdigest()

    @staticmethod
    def _get_default_user():
        """Return the first superuser as a fallback owner."""
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.filter(is_superuser=True).first()
        if not user:
            user = User.objects.filter(is_staff=True).first()
        if not user:
            user = User.objects.first()
        if not user:
            logger.warning("No user found in database. Cannot assign PipelineProperty owner.")
        return user

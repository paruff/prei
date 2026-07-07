"""VRM Properties discovery source — converts VRM foreclosure listings
into pipeline-compatible dicts for the DiscoveryProcessor.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from prei.pipeline.sources.base import DiscoverySource

logger = logging.getLogger(__name__)


class VrmDiscoverySource(DiscoverySource):
    """Bridge source that queries existing VRM foreclosure data.

    Unlike the REO sources (Fannie Mae, HUD, etc.), this source reads
    from the Django VrmProperty model rather than scraping external APIs.
    This makes it immediately usable as a proof-of-concept, then replaced
    or augmented with external scrapers as they're built.
    """

    @property
    def name(self) -> str:
        return "vrm"

    def fetch(
        self,
        state: str,
        zip_code: Optional[str] = None,
        limit: int = 200,
        status_filter: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """Fetch VRM properties for a state/zip as pipeline-compatible dicts.

        Args:
            state: Two-letter state code.
            zip_code: Optional ZIP code filter.
            limit: Max records to return (default 200).
            status_filter: Optional list of VrmProperty.Status values to
                           include. Defaults to for_sale + coming_soon.

        Returns:
            List of dicts compatible with DiscoverySanitizer.transform_input().
        """
        try:
            import django
            import os

            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "investor_app.settings")
            django.setup()

            from core.models import VrmProperty  # noqa: F811
        except Exception as exc:
            logger.error("VRM source failed to init Django: %s", exc)
            return []

        statuses = status_filter or ["for_sale", "coming_soon"]
        qs = VrmProperty.objects.filter(
            state__iexact=state.strip().upper(),
            status__in=statuses,
        ).order_by("-last_seen_at")[:limit]

        if zip_code:
            qs = qs.filter(zip_code__startswith=zip_code)

        listings = []
        for prop in qs:
            listings.append(
                {
                    "id": f"vrm-{prop.vrm_property_id}",
                    "address": f"{prop.address}, {prop.city}, {prop.state} {prop.zip_code}",
                    "price": float(prop.list_price) if prop.list_price else None,
                    "rent": float(prop.projected_monthly_rent)
                    if prop.projected_monthly_rent
                    else None,
                    "beds": None,  # VRM listings don't always include bed count
                    "baths": None,
                    "sqft": None,
                    "source_url": prop.vrm_listing_url,
                    "status": prop.status,
                }
            )

        logger.info(
            "VRM source fetched %d properties for %s (zip=%s, statuses=%s)",
            len(listings),
            state,
            zip_code or "any",
            statuses,
        )
        return listings

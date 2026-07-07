"""Memory-efficient deduplication and ingestion engine for the DISCOVERY stage.

Processes thousands of incoming records from a discovery sweep, cross-referencing
against existing historical entries via address hashes to eliminate duplicate
data before allocating state tracking blocks.
"""

from __future__ import annotations

from typing import Any, Dict, List, Set

from prei.models.pipeline import PipelineStage, PropertyAsset
from prei.pipeline.handlers.discovery import DiscoverySanitizer


class DiscoveryProcessor:
    """Deduplicating ingestion processor for the DISCOVERY pipeline stage.

    Compares incoming batch address hashes against existing entries to
    eliminate duplicates, then instantiates PropertyAsset records for
    newly discovered properties at PipelineStage.DISCOVERY.

    Args:
        existing_hashes: Set of SHA-256 address hashes already known to
                         the persistent storage layer.
    """

    def __init__(self, existing_hashes: Set[str]) -> None:
        self.existing_hashes = existing_hashes

    def process_batch(
        self,
        raw_listings: List[Dict[str, Any]],
        source_name: str,
    ) -> Dict[str, Any]:
        """Process a batch of raw listings through dedup and state inception.

        Each listing is:
          1. Normalised via DiscoverySanitizer.transform_input()
          2. Checked for address_hash collision against existing_hashes
          3. If duplicate → counted and skipped
          4. If new → PropertyAsset created at DISCOVERY, hash added

        Args:
            raw_listings: List of raw property data dicts from an external
                          source (MLS, county records, wholesale JSON, etc.).
            source_name: Human-readable source label (e.g. "mls_feed",
                         "county_scraper").

        Returns:
            Analytics dict:
                total_received        (int): Raw count of input records.
                new_assets_discovered (int): Assets created.
                duplicates_skipped    (int): Records rejected by hash match.
                failed_records        (int): Records that raised during parsing.
                payloads         (list[PropertyAsset]): Newly created assets.
        """
        new_assets: List[PropertyAsset] = []
        duplicates_count = 0
        errors_count = 0

        for raw in raw_listings:
            try:
                canonical = DiscoverySanitizer.transform_input(raw, source_name)

                if canonical.address_hash in self.existing_hashes:
                    duplicates_count += 1
                    continue

                # Create asset at GACS, then transition to DISCOVERY to
                # seed the initial stage log entry with financial context.
                asset = PropertyAsset(
                    asset_id=canonical.source_id,
                    address=canonical.raw_address,
                )
                asset.transition_to(
                    PipelineStage.DISCOVERY,
                    reason="Initial discovery ingestion",
                    metrics={
                        "source": source_name,
                        "purchase_price": canonical.price,
                        "estimated_rent": canonical.estimated_rent,
                        "sqft": canonical.sqft,
                        "year_built": canonical.year_built,
                    },
                )

                new_assets.append(asset)
                self.existing_hashes.add(canonical.address_hash)

            except Exception:
                errors_count += 1
                continue

        return {
            "total_received": len(raw_listings),
            "new_assets_discovered": len(new_assets),
            "duplicates_skipped": duplicates_count,
            "failed_records": errors_count,
            "payloads": new_assets,
        }

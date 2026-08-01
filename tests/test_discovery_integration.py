"""Integration tests for the discovery stage — components working together.

Tests how DiscoverySanitizer, the discovery processor, and data sources
integrate with each other and with the downstream screening/underwriting
services (the prei orchestrator class was deleted in the pydantic→Django
consolidation; orchestration is now explicit service composition).
"""

from typing import Any

from core.services.discovery import DiscoverySanitizer
from core.services.discovery_processor import process_discovery_batch
from core.services.screening import ScreeningThresholds, screen_batch
from core.services.sources.county import TexasCountyForeclosureSource
from core.services.sources.registry import discover_from_all, get_source

# ── Fixtures ──────────────────────────────────────────────────────────────────

MLS_BATCH: list[dict[str, Any]] = [
    {
        "id": "MLS-001",
        "address": "123 Main St.",
        "price": 300_000.0,
        "rent": 2500.0,
        "beds": 3,
        "baths": 2,
        "sqft": 1800,
    },
    {
        "id": "MLS-002",
        "address": "456 Oak Ave",
        "price": 250_000.0,
        "rent": 2000.0,
        "beds": 2,
        "baths": 1,
    },
    {
        "id": "MLS-003",
        "address": "789 Pine Rd",
        "price": 400_000.0,
        "rent": 3200.0,
        "beds": 4,
        "baths": 3,
        "sqft": 2200,
    },
]

COUNTY_BATCH: list[dict[str, Any]] = [
    {
        "parcel_id": "PCN-101",
        "FullStreetAddress": "101 Foreclosure Dr",
        "sale_price": 180_000.0,
        "BedroomsTotal": "3",
        "BathroomsTotalInteger": "2",
        "LivingArea": "1500",
    },
    {
        "parcel_id": "PCN-102",
        "FullStreetAddress": "202 Default Ln",
        "sale_price": 220_000.0,
        "BedroomsTotal": "4",
        "BathroomsTotalInteger": "2.5",
    },
]


# ═══════════════════════════════════════════════════════════════════════════════
#  1. Sanitizer → Processor integration
# ═══════════════════════════════════════════════════════════════════════════════


class TestSanitizerToProcessor:
    """DiscoverySanitizer output feeds directly into the processor."""

    def test_sanitizer_output_matches_processor_input(self):
        """CanonicalPropertyPayload fields map correctly to processor expectations."""
        raw = MLS_BATCH[0]
        canonical = DiscoverySanitizer.transform_input(raw, source="mls")
        assert canonical.source_id == "MLS-001"
        assert canonical.price == 300_000.0
        assert canonical.address_hash is not None
        assert len(canonical.address_hash) == 64

    def test_processor_uses_correct_hash(self):
        """Processor dedup uses same hash as sanitizer produces."""
        canonical = DiscoverySanitizer.transform_input(MLS_BATCH[0], "test")
        result = process_discovery_batch(
            MLS_BATCH, source_name="test", existing_hashes={canonical.address_hash}
        )
        # MLS-001 is duplicate (hash pre-populated)
        # MLS-002 and MLS-003 are new
        assert result["new_assets_discovered"] == 2
        assert result["duplicates_skipped"] == 1

    def test_processor_outputs_are_canonical_payloads(self):
        """Processor returns canonical payloads with source identity."""
        result = process_discovery_batch(MLS_BATCH[:1], source_name="test")
        assert len(result["payloads"]) == 1
        payload = result["payloads"][0]
        assert payload.source_id == "MLS-001"
        assert "123 main st" in payload.raw_address.lower()


# ═══════════════════════════════════════════════════════════════════════════════
#  2. Multi-source batch processing
# ═══════════════════════════════════════════════════════════════════════════════


class TestMultiSourceProcessing:
    """Different source schemas all flow through the same processor."""

    def test_mls_schema_processed(self):
        """MLS-format listings produce valid payloads."""
        result = process_discovery_batch(MLS_BATCH, source_name="mls")
        assert result["new_assets_discovered"] == 3
        assert result["failed_records"] == 0

    def test_county_schema_processed(self):
        """County-foreclosure-format listings produce valid payloads."""
        result = process_discovery_batch(COUNTY_BATCH, source_name="county")
        assert result["new_assets_discovered"] == 2
        assert result["failed_records"] == 0

    def test_mixed_source_deduplication(self):
        """Same address from different sources matches via hash."""
        existing: set[str] = set()
        # Process MLS batch first
        r1 = process_discovery_batch(
            MLS_BATCH, source_name="mls", existing_hashes=existing
        )
        assert r1["new_assets_discovered"] == 3

        # Process a batch containing a duplicate address in county format
        duplicate = {
            "parcel_id": "DUP-001",
            "FullStreetAddress": "123 Main St.",  # same as MLS-001
            "sale_price": 310_000.0,
        }
        r2 = process_discovery_batch(
            [duplicate], source_name="county", existing_hashes=existing
        )
        assert r2["new_assets_discovered"] == 0
        assert r2["duplicates_skipped"] == 1

    def test_empty_batch_mixed_sources(self):
        """Empty batches from any source produce zero results."""
        for source_name in ["mls", "county", "fannie_mae"]:
            result = process_discovery_batch([], source_name=source_name)
            assert result["total_received"] == 0
            assert result["new_assets_discovered"] == 0


# ═══════════════════════════════════════════════════════════════════════════════
#  3. Source registry → Processor integration
# ═══════════════════════════════════════════════════════════════════════════════


class TestSourceRegistryToProcessor:
    """Source registry fetchers feed data into the processor."""

    def test_fannie_mae_source_returns_list(self):
        """Source fetch returns a list (may be empty placeholder)."""
        source = get_source("fannie_mae")
        listings = source.fetch(state="CA")
        assert isinstance(listings, list)

    def test_county_source_supported_counties(self):
        """County source knows supported counties for active states."""
        counties = TexasCountyForeclosureSource.available_counties()
        assert "harris" in counties

    def test_discover_from_all_returns_dict(self):
        """discover_from_all returns source_name → list mapping."""
        results = discover_from_all(state="CA", source_filter=["fannie_mae", "hud"])
        assert isinstance(results, dict)
        assert "fannie_mae" in results
        assert "hud" in results


# ═══════════════════════════════════════════════════════════════════════════════
#  4. Dedup across batches (shared hash set)
# ═══════════════════════════════════════════════════════════════════════════════


class TestCrossBatchDeduplication:
    """Shared hash set dedups across multiple batches."""

    def test_shared_hashes_multiple_batches(self):
        """Same hash set across batches dedups."""
        existing: set[str] = set()

        r1 = process_discovery_batch(
            MLS_BATCH[:2], source_name="mls", existing_hashes=existing
        )
        assert r1["new_assets_discovered"] == 2

        r2 = process_discovery_batch(
            MLS_BATCH[2:], source_name="mls", existing_hashes=existing
        )
        assert r2["new_assets_discovered"] == 1

        r3 = process_discovery_batch(
            MLS_BATCH, source_name="mls", existing_hashes=existing
        )
        assert r3["new_assets_discovered"] == 0
        assert r3["duplicates_skipped"] == 3

    def test_separate_hash_sets_independent(self):
        """Different hash sets are independent."""
        p1: set[str] = set()
        p2: set[str] = set()
        process_discovery_batch(MLS_BATCH, source_name="mls", existing_hashes=p1)
        process_discovery_batch(MLS_BATCH, source_name="mls", existing_hashes=p2)
        # Both should have discovered all 3 since their hash sets started empty
        assert len(p1) == 3
        assert len(p2) == 3

    def test_existing_hashes_persistence(self):
        """existing_hashes set is mutated in-place after each batch."""
        hashes: set[str] = set()
        process_discovery_batch(MLS_BATCH, source_name="test", existing_hashes=hashes)
        assert len(hashes) == 3


# ═══════════════════════════════════════════════════════════════════════════════
#  5. Discovery → Screening → Underwriting composition
# ═══════════════════════════════════════════════════════════════════════════════


class TestDiscoveryToDownstreamServices:
    """Discovery payloads feed into screening and underwriting (orchestrator
    equivalent — the prei orchestrator class was deleted)."""

    def test_discovered_payload_runs_through_screening(self):
        """A discovered payload can be screened with standard thresholds."""
        result = process_discovery_batch(MLS_BATCH[:1], source_name="mls")
        payload = result["payloads"][0]
        threshold = ScreeningThresholds(
            min_gross_yield=0.07,
            max_price_to_rent_ratio=15.0,
            min_beds=2,
            min_baths=1,
        )
        screening = screen_batch(
            [
                {
                    "asset_id": payload.source_id,
                    "address": payload.raw_address,
                    "estimated_monthly_rent": payload.estimated_rent,
                    "purchase_price": payload.price,
                    "beds": payload.beds,
                    "baths": payload.baths,
                }
            ],
            threshold,
        )
        # MLS-001: (2500*12)/300000 = 10% yield, ratio 10 → passes
        assert screening["advanced"] == 1
        assert screening["killed"] == 0

    def test_duplicate_payload_rejected_at_discovery(self):
        """Same address twice → second run discovers nothing."""
        existing: set[str] = set()
        r1 = process_discovery_batch(
            MLS_BATCH[:1], source_name="mls", existing_hashes=existing
        )
        assert r1["new_assets_discovered"] == 1
        r2 = process_discovery_batch(
            MLS_BATCH[:1], source_name="mls", existing_hashes=existing
        )
        assert r2["new_assets_discovered"] == 0
        assert r2["duplicates_skipped"] == 1

    def test_missing_address_fails_gracefully(self):
        """Address-less payload is counted as failed, not raised."""
        result = process_discovery_batch([{"id": "BAD"}], source_name="test")
        assert result["failed_records"] == 1
        assert result["new_assets_discovered"] == 0


# ═══════════════════════════════════════════════════════════════════════════════
#  6. Large batch stress test
# ═══════════════════════════════════════════════════════════════════════════════


class TestLargeBatchProcessing:
    """Stress-tests with large batches."""

    def test_1000_unique_listings(self):
        """1000 unique listings processed with zero failures."""
        batch = [
            {
                "id": f"STRESS-{i:04d}",
                "address": f"{i} Stress Test Blvd",
                "price": 200_000.0 + i * 100,
                "beds": 3,
                "baths": 2,
            }
            for i in range(1000)
        ]
        result = process_discovery_batch(batch, source_name="stress")
        assert result["total_received"] == 1000
        assert result["new_assets_discovered"] == 1000
        assert result["duplicates_skipped"] == 0
        assert result["failed_records"] == 0

    def test_1000_listings_50_percent_duplicates(self):
        """500 unique + 500 duplicates = 500 discovered."""
        batch = [
            {
                "id": f"UNIQ-{i:04d}",
                "address": f"{i} Unique Dr",
                "price": 300_000.0,
                "beds": 3,
                "baths": 2,
            }
            for i in range(500)
        ]
        # Add 500 exact duplicates
        for i in range(500):
            batch.append(
                {
                    "id": f"DUP-{i:04d}",
                    "address": f"{i} Unique Dr",
                    "price": 300_000.0,
                    "beds": 3,
                    "baths": 2,
                }
            )
        result = process_discovery_batch(batch, source_name="stress")
        assert result["new_assets_discovered"] == 500
        assert result["duplicates_skipped"] == 500
        assert result["failed_records"] == 0

    def test_malformed_listings_dont_crash_batch(self):
        """Malformed records are counted as failed, rest process normally."""
        batch = [
            *MLS_BATCH,
            {"no_address": True},  # bad
            {"id": "BAD", "price": 100},  # bad — no address
            *COUNTY_BATCH,
        ]
        result = process_discovery_batch(batch, source_name="mixed")
        # 3 MLS + 2 county = 5 valid, 2 bad
        assert result["new_assets_discovered"] == 5
        assert result["failed_records"] == 2

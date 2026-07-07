"""Integration tests for the discovery stage — components working together.

Tests how DiscoverySanitizer, DiscoveryProcessor, and data sources
integrate with each other and with the PipelineOrchestrator.
"""

from prei.models.pipeline import PipelineStage
from prei.pipeline.handlers.discovery import DiscoverySanitizer
from prei.pipeline.handlers.discovery_processor import DiscoveryProcessor
from prei.pipeline.orchestrator import PipelineOrchestrator
from prei.pipeline.sources.county import TexasCountyForeclosureSource
from prei.pipeline.sources.registry import discover_from_all, get_source

# ── Fixtures ──────────────────────────────────────────────────────────────────

MLS_BATCH = [
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

COUNTY_BATCH = [
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
    """DiscoverySanitizer output feeds directly into DiscoveryProcessor."""

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
        proc = DiscoveryProcessor(existing_hashes={canonical.address_hash})
        result = proc.process_batch(MLS_BATCH, source_name="test")
        # MLS-001 is duplicate (hash pre-populated)
        # MLS-002 and MLS-003 are new
        assert result["new_assets_discovered"] == 2
        assert result["duplicates_skipped"] == 1

    def test_processor_outputs_are_property_assets(self):
        """Processor returns PropertyAsset instances with correct stage."""
        proc = DiscoveryProcessor(existing_hashes=set())
        result = proc.process_batch(MLS_BATCH[:1], source_name="test")
        assert len(result["payloads"]) == 1
        asset = result["payloads"][0]
        assert asset.current_stage == PipelineStage.DISCOVERY
        assert asset.asset_id == "MLS-001"
        assert "123 main st" in asset.address.lower()


# ═══════════════════════════════════════════════════════════════════════════════
#  2. Multi-source batch processing
# ═══════════════════════════════════════════════════════════════════════════════


class TestMultiSourceProcessing:
    """Different source schemas all flow through the same processor."""

    def test_mls_schema_processed(self):
        """MLS-format listings produce valid assets."""
        proc = DiscoveryProcessor(existing_hashes=set())
        result = proc.process_batch(MLS_BATCH, source_name="mls")
        assert result["new_assets_discovered"] == 3
        assert result["failed_records"] == 0

    def test_county_schema_processed(self):
        """County-foreclosure-format listings produce valid assets."""
        proc = DiscoveryProcessor(existing_hashes=set())
        result = proc.process_batch(COUNTY_BATCH, source_name="county")
        assert result["new_assets_discovered"] == 2
        assert result["failed_records"] == 0

    def test_mixed_source_deduplication(self):
        """Same address from different sources matches via hash."""
        proc = DiscoveryProcessor(existing_hashes=set())
        # Process MLS batch first
        r1 = proc.process_batch(MLS_BATCH, source_name="mls")
        assert r1["new_assets_discovered"] == 3

        # Process a batch containing a duplicate address in county format
        duplicate = {
            "parcel_id": "DUP-001",
            "FullStreetAddress": "123 Main St.",  # same as MLS-001
            "sale_price": 310_000.0,
        }
        r2 = proc.process_batch([duplicate], source_name="county")
        assert r2["new_assets_discovered"] == 0
        assert r2["duplicates_skipped"] == 1

    def test_empty_batch_mixed_sources(self):
        """Empty batches from any source produce zero results."""
        for source_name in ["mls", "county", "fannie_mae"]:
            proc = DiscoveryProcessor(existing_hashes=set())
            result = proc.process_batch([], source_name=source_name)
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
#  4. Dedup across batches (stateful processor)
# ═══════════════════════════════════════════════════════════════════════════════


class TestCrossBatchDeduplication:
    """Processor maintains state across multiple batches."""

    def test_same_processor_multiple_batches(self):
        """Same processor instance dedups across batches."""
        proc = DiscoveryProcessor(existing_hashes=set())

        r1 = proc.process_batch(MLS_BATCH[:2], source_name="mls")
        assert r1["new_assets_discovered"] == 2

        r2 = proc.process_batch(MLS_BATCH[2:], source_name="mls")
        assert r2["new_assets_discovered"] == 1

        r3 = proc.process_batch(MLS_BATCH, source_name="mls")
        assert r3["new_assets_discovered"] == 0
        assert r3["duplicates_skipped"] == 3

    def test_separate_processors_independent(self):
        """Different processor instances have independent hash sets."""
        p1 = DiscoveryProcessor(existing_hashes=set())
        p2 = DiscoveryProcessor(existing_hashes=set())
        p1.process_batch(MLS_BATCH, source_name="mls")
        p2.process_batch(MLS_BATCH, source_name="mls")
        # Both should have discovered all 3 since their hash sets started empty
        assert len(p1.existing_hashes) == 3
        assert len(p2.existing_hashes) == 3

    def test_existing_hashes_persistence(self):
        """existing_hashes set is mutated in-place after each batch."""
        hashes: set = set()
        proc = DiscoveryProcessor(existing_hashes=hashes)
        proc.process_batch(MLS_BATCH, source_name="test")
        assert len(hashes) == 3


# ═══════════════════════════════════════════════════════════════════════════════
#  5. Processor → PipelineOrchestrator integration
# ═══════════════════════════════════════════════════════════════════════════════


class TestProcessorToOrchestrator:
    """DiscoveryProcessor output feeds into PipelineOrchestrator."""

    def test_discovered_asset_can_run_through_orchestrator(self):
        """An asset discovered by processor can be pipelined through orchestrator."""
        proc = DiscoveryProcessor(existing_hashes=set())
        result = proc.process_batch(MLS_BATCH[:1], source_name="mls")
        asset = result["payloads"][0]
        assert asset.current_stage == PipelineStage.DISCOVERY

        # The orchestrator would take the raw payload directly
        orch = PipelineOrchestrator(existing_hashes=set())
        or_result = orch.run(MLS_BATCH[0], source_name="mls")
        assert or_result.success
        assert or_result.asset.current_stage == PipelineStage.UNDERWRITING

    def test_orchestrator_rejects_duplicates(self):
        """Orchestrator rejects duplicate address hashes."""
        orch = PipelineOrchestrator(existing_hashes=set())
        r1 = orch.run(MLS_BATCH[0], source_name="mls")
        assert r1.success
        r2 = orch.run(MLS_BATCH[0], source_name="mls")
        assert r2.success is False
        assert "Duplicate" in (r2.error or "")

    def test_orchestrator_fails_missing_address(self):
        """Orchestrator fails gracefully on address-less payload."""
        orch = PipelineOrchestrator()
        result = orch.run({"id": "BAD"}, source_name="test")
        assert result.success is False
        assert "Discovery" in (result.error or "")


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
        proc = DiscoveryProcessor(existing_hashes=set())
        result = proc.process_batch(batch, source_name="stress")
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
        proc = DiscoveryProcessor(existing_hashes=set())
        result = proc.process_batch(batch, source_name="stress")
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
        proc = DiscoveryProcessor(existing_hashes=set())
        result = proc.process_batch(batch, source_name="mixed")
        # 3 MLS + 2 county = 5 valid, 2 bad
        assert result["new_assets_discovered"] == 5
        assert result["failed_records"] == 2

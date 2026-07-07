"""Tests for the DiscoveryProcessor deduplication engine."""

from prei.models.pipeline import PipelineStage
from prei.pipeline.handlers.discovery_processor import DiscoveryProcessor

# ── Sample raw listing payloads ───────────────────────────────────────────────

LISTING_A = {
    "id": "MLS-001",
    "address": "123 Main St.",
    "price": 300_000.0,
    "beds": 3,
    "baths": 2,
    "sqft": 1800,
}

LISTING_B = {
    "id": "MLS-002",
    "address": "456 Oak Ave",
    "price": 250_000.0,
    "beds": 4,
    "baths": 2.5,
}

LISTING_C = {
    "id": "MLS-003",
    "address": "123 Main St.",  # Same address as A — duplicate after normalization
    "price": 310_000.0,
    "beds": 3,
    "baths": 2,
}

LISTING_D = {
    "id": "MLS-004",
    "address": "789 Pine Rd",
    "price": 400_000.0,
    "beds": 5,
    "baths": 3,
}

LISTING_NO_ADDRESS = {
    "id": "MLS-BAD",
    "price": 200_000,
    "beds": 2,
    "baths": 1,
}


# ═══════════════════════════════════════════════════════════════════════════════


class TestDiscoveryProcessor:
    """Tests for the deduplication and ingestion engine."""

    # ── Basic flow ────────────────────────────────────────────────────────────

    def test_empty_batch(self):
        """Empty batch returns zero counts and empty payloads."""
        proc = DiscoveryProcessor(existing_hashes=set())
        result = proc.process_batch([], source_name="test")
        assert result["total_received"] == 0
        assert result["new_assets_discovered"] == 0
        assert result["duplicates_skipped"] == 0
        assert result["failed_records"] == 0
        assert result["payloads"] == []

    def test_single_new_asset(self):
        """Single new listing creates one PropertyAsset at DISCOVERY."""
        proc = DiscoveryProcessor(existing_hashes=set())
        result = proc.process_batch([LISTING_A], source_name="mls_feed")
        assert result["total_received"] == 1
        assert result["new_assets_discovered"] == 1
        assert result["duplicates_skipped"] == 0
        assert result["failed_records"] == 0
        assert len(result["payloads"]) == 1

        asset = result["payloads"][0]
        assert asset.asset_id == "MLS-001"
        assert asset.current_stage == PipelineStage.DISCOVERY
        assert len(asset.stage_history) == 1
        assert asset.stage_history[0].stage == PipelineStage.DISCOVERY
        assert asset.stage_history[0].reason == "Initial discovery ingestion"

    def test_all_new_assets(self):
        """Multiple new listings all create assets."""
        proc = DiscoveryProcessor(existing_hashes=set())
        result = proc.process_batch(
            [LISTING_A, LISTING_B, LISTING_D], source_name="test"
        )
        assert result["total_received"] == 3
        assert result["new_assets_discovered"] == 3
        assert result["duplicates_skipped"] == 0
        assert result["failed_records"] == 0

    # ── Deduplication ────────────────────────────────────────────────────────

    def test_duplicate_by_normalized_address(self):
        """Same normalised address (even with different formatting) → duplicate."""
        proc = DiscoveryProcessor(existing_hashes=set())
        result = proc.process_batch([LISTING_A, LISTING_C], source_name="test")
        assert result["total_received"] == 2
        assert result["new_assets_discovered"] == 1  # A is new, C is duplicate
        assert result["duplicates_skipped"] == 1

    def test_duplicate_via_existing_hashes(self):
        """Pre-populated existing hashes prevent creation."""
        # Compute the hash that LISTING_A would produce
        from prei.pipeline.handlers.discovery import DiscoverySanitizer

        canonical_a = DiscoverySanitizer.transform_input(LISTING_A, "test")
        proc = DiscoveryProcessor(existing_hashes={canonical_a.address_hash})
        result = proc.process_batch([LISTING_A, LISTING_B], source_name="test")
        assert result["new_assets_discovered"] == 1  # only B
        assert result["duplicates_skipped"] == 1  # A skipped

    # ── Error handling ────────────────────────────────────────────────────────

    def test_missing_address_skipped_as_failed(self):
        """Listing without valid address counts as failed_record."""
        proc = DiscoveryProcessor(existing_hashes=set())
        result = proc.process_batch([LISTING_A, LISTING_NO_ADDRESS], source_name="test")
        assert result["total_received"] == 2
        assert result["new_assets_discovered"] == 1  # only A
        assert result["failed_records"] == 1  # no-address failed

    def test_all_failed_records(self):
        """All records failing returns zero new assets."""
        proc = DiscoveryProcessor(existing_hashes=set())
        result = proc.process_batch(
            [LISTING_NO_ADDRESS, {"no": "data"}], source_name="test"
        )
        assert result["new_assets_discovered"] == 0
        assert result["failed_records"] == 2

    # ── Mixed batch ───────────────────────────────────────────────────────────

    def test_mixed_batch_counts(self):
        """Mixed batch with new, duplicate, and failed records."""
        proc = DiscoveryProcessor(existing_hashes=set())
        result = proc.process_batch(
            [LISTING_A, LISTING_B, LISTING_C, LISTING_D, LISTING_NO_ADDRESS],
            source_name="test",
        )
        # A: new, B: new, C: dup of A, D: new, NO_ADDRESS: failed
        assert result["total_received"] == 5
        assert result["new_assets_discovered"] == 3  # A, B, D
        assert result["duplicates_skipped"] == 1  # C
        assert result["failed_records"] == 1  # NO_ADDRESS

    # ── Financial data in stage log ──────────────────────────────────────────

    def test_financials_in_stage_log_metrics(self):
        """Purchase price and estimated rent stored in stage_log metrics."""
        proc = DiscoveryProcessor(existing_hashes=set())
        result = proc.process_batch(
            [
                {
                    "id": "FIN-001",
                    "address": "100 Finance Blvd",
                    "price": 500_000.0,
                    "rent": 4000.0,
                    "beds": 4,
                    "baths": 3,
                }
            ],
            source_name="test",
        )
        asset = result["payloads"][0]
        metrics = asset.stage_history[0].metrics_snapshot
        assert metrics["purchase_price"] == 500_000.0
        assert metrics["estimated_rent"] == 4000.0
        assert metrics["source"] == "test"

    # ── Existing hashes updated after processing ─────────────────────────────

    def test_existing_hashes_updated(self):
        """New address hashes are added to the existing_hashes set."""
        from prei.pipeline.handlers.discovery import DiscoverySanitizer

        proc = DiscoveryProcessor(existing_hashes=set())
        proc.process_batch([LISTING_A, LISTING_B], source_name="test")

        hash_a = DiscoverySanitizer.compute_address_hash(
            DiscoverySanitizer.clean_address(LISTING_A["address"])
        )
        hash_b = DiscoverySanitizer.compute_address_hash(
            DiscoverySanitizer.clean_address(LISTING_B["address"])
        )
        assert hash_a in proc.existing_hashes
        assert hash_b in proc.existing_hashes

    # ── Deterministic ─────────────────────────────────────────────────────────

    def test_deterministic_same_input(self):
        """Same input list produces identical counts."""
        p1 = DiscoveryProcessor(existing_hashes=set())
        p2 = DiscoveryProcessor(existing_hashes=set())
        listings = [LISTING_A, LISTING_B, LISTING_C]
        r1 = p1.process_batch(listings, "test")
        r2 = p2.process_batch(listings, "test")
        for key in (
            "total_received",
            "new_assets_discovered",
            "duplicates_skipped",
            "failed_records",
        ):
            assert r1[key] == r2[key]

    # ── Large batch performance ───────────────────────────────────────────────

    def test_large_batch_1000(self):
        """1000 unique listings processed quickly."""
        proc = DiscoveryProcessor(existing_hashes=set())
        listings = [
            {
                "id": f"BATCH-{i:04d}",
                "address": f"{i} Unique St",
                "price": float(200_000 + i * 1000),
                "beds": 3,
                "baths": 2,
            }
            for i in range(1000)
        ]
        result = proc.process_batch(listings, source_name="bulk")
        assert result["total_received"] == 1000
        assert result["new_assets_discovered"] == 1000
        assert result["duplicates_skipped"] == 0
        assert result["failed_records"] == 0
        assert len(result["payloads"]) == 1000

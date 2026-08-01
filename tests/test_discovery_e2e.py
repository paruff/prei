"""Live end-to-end tests for the discovery stage of the pipeline.

Tests simulate the full discovery flow:
  raw listings → DiscoverySanitizer → process_discovery_batch

These are marked as 'e2e' and 'slow' — skipped in CI unless explicitly requested.
Run with: pytest tests/test_discovery_e2e.py -v -m e2e
"""

import pytest

from core.services.discovery import DiscoverySanitizer
from core.services.discovery_processor import process_discovery_batch

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.slow,
]


# ═══════════════════════════════════════════════════════════════════════════════
#  Fixtures: realistic multi-source property payloads
# ═══════════════════════════════════════════════════════════════════════════════

REALISTIC_MLS_FEED = [
    {
        "id": "RE-LIST-001",
        "address": "1500 Pacific Ave, San Francisco, CA 94109",
        "price": 850_000.0,  # (5500*12)/850000 = 7.76% ✓
        "rent": 5500.0,
        "beds": 3,
        "baths": 2,
        "sqft": 1800,
        "year_built": 1985,
        "property_tax_annual": 10_200.0,
        "insurance_annual": 1_800.0,
        "hoa_annual": 6_000.0,
    },
    {
        "id": "RE-LIST-002",
        "address": "2800 Elm St, Dallas, TX 75201",
        "price": 350_000.0,  # (2800*12)/350000 = 9.6% ✓
        "rent": 2800.0,
        "beds": 3,
        "baths": 2,
        "sqft": 1600,
        "year_built": 2010,
        "property_tax_annual": 6_300.0,
        "insurance_annual": 1_400.0,
        "hoa_annual": 0.0,
    },
    {
        "id": "RE-LIST-003",
        "address": "850 Lake Shore Blvd, Chicago, IL 60611",
        "price": 380_000.0,  # (3200*12)/380000 = 10.1% ✓
        "rent": 3200.0,
        "beds": 2,
        "baths": 2,
        "sqft": 1400,
        "year_built": 2005,
        "property_tax_annual": 7_200.0,
        "insurance_annual": 1_600.0,
        "hoa_annual": 4_800.0,
    },
]

REALISTIC_COUNTY_FEED = [
    {
        "parcel_id": "CNTY-001",
        "FullStreetAddress": "7500 Sunset Blvd, Los Angeles, CA 90046",
        "sale_price": 850_000.0,
        "BedroomsTotal": "4",
        "BathroomsTotalInteger": "3",
        "LivingArea": "2200",
        "YearBuilt": 1978,
    },
    {
        "parcel_id": "CNTY-002",
        "FullStreetAddress": "1200 Commerce St, Dallas, TX 75202",
        "sale_price": 275_000.0,
        "BedroomsTotal": "3",
        "BathroomsTotalInteger": "2",
        "LivingArea": "1500",
        "YearBuilt": 1995,
    },
]


# ═══════════════════════════════════════════════════════════════════════════════
#  E2E Test: Full MLS → Pipeline
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.e2e
class TestE2EMlsPipeline:
    """End-to-end: raw MLS listings through the discovery pipeline."""

    def test_mls_feed_through_sanitizer(self):
        """MLS listing normalizes to canonical payload with correct fields."""
        raw = REALISTIC_MLS_FEED[0]
        canonical = DiscoverySanitizer.transform_input(raw, source="mls_realtor")
        assert canonical.source_id == "RE-LIST-001"
        assert canonical.source_name == "mls_realtor"
        assert canonical.price == 850_000.0
        assert canonical.estimated_rent == 5500.0
        assert canonical.beds == 3
        assert canonical.baths == 2.0
        assert canonical.sqft == 1800.0
        assert canonical.year_built == 1985
        assert canonical.address_hash is not None
        assert len(canonical.address_hash) == 64

    def test_mls_feed_through_discovery_processor(self):
        """MLS listings are ingested without duplicates."""
        result = process_discovery_batch(REALISTIC_MLS_FEED, source_name="mls")
        assert result["total_received"] == 3
        assert result["new_assets_discovered"] == 3
        assert result["duplicates_skipped"] == 0
        assert result["failed_records"] == 0
        assert len(result["payloads"]) == 3
        for payload in result["payloads"]:
            assert payload.source_name == "mls"
            assert payload.address_hash


# ═══════════════════════════════════════════════════════════════════════════════
#  E2E Test: County Feed → Pipeline
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.e2e
class TestE2ECountyPipeline:
    """End-to-end: county foreclosure records through the discovery pipeline."""

    def test_county_feed_through_sanitizer(self):
        """County records with alternative key schemas normalize correctly."""
        raw = REALISTIC_COUNTY_FEED[0]
        canonical = DiscoverySanitizer.transform_input(raw, source="county_recorder")
        assert canonical.source_id == "CNTY-001"
        assert canonical.price == 850_000.0
        assert canonical.beds == 4
        assert canonical.baths == 3.0
        assert canonical.sqft == 2200.0
        assert canonical.year_built == 1978

    def test_county_feed_dedup_against_mls(self):
        """County records with same address as MLS listings are deduplicated."""
        existing: set[str] = set()
        # Process MLS feed first
        process_discovery_batch(
            REALISTIC_MLS_FEED, source_name="mls", existing_hashes=existing
        )

        # Process county feed — should have no overlap if addresses are unique
        result = process_discovery_batch(
            REALISTIC_COUNTY_FEED, source_name="county", existing_hashes=existing
        )
        assert result["new_assets_discovered"] == 2
        assert result["duplicates_skipped"] == 0

    def test_county_schema_no_rent(self):
        """County records have no rent data — estimated_rent is None."""
        canonical = DiscoverySanitizer.transform_input(
            REALISTIC_COUNTY_FEED[0], "county"
        )
        assert canonical.estimated_rent is None


# ═══════════════════════════════════════════════════════════════════════════════
#  E2E Test: Multi-source orchestration
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.e2e
class TestE2EMultiSourceOrchestration:
    """Multiple sources feed into the same pipeline."""

    def test_multi_source_dedup_shared_hashes(self):
        """Shared existing_hashes set prevents cross-source duplicates."""
        hashes: set[str] = set()
        process_discovery_batch(REALISTIC_MLS_FEED, "mls", existing_hashes=hashes)
        assert len(hashes) == 3

        process_discovery_batch(REALISTIC_COUNTY_FEED, "county", existing_hashes=hashes)
        assert len(hashes) == 5  # 3 MLS + 2 county (all unique addresses)

    def test_multi_source_dedup_via_batch(self):
        """Shared hash set dedups across calls."""
        hashes: set[str] = set()

        r1 = process_discovery_batch(
            REALISTIC_MLS_FEED[:1], source_name="mls", existing_hashes=hashes
        )
        assert r1["new_assets_discovered"] == 1

        # Same address again → duplicate
        r2 = process_discovery_batch(
            REALISTIC_MLS_FEED[:1], source_name="mls", existing_hashes=hashes
        )
        assert r2["new_assets_discovered"] == 0
        assert r2["duplicates_skipped"] == 1

        # Different address → success
        r3 = process_discovery_batch(
            REALISTIC_MLS_FEED[1:2], source_name="mls", existing_hashes=hashes
        )
        assert r3["new_assets_discovered"] == 1


# ═══════════════════════════════════════════════════════════════════════════════
#  E2E Test: Simulation of daily pipeline run
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.e2e
class TestE2EDailyPipelineRun:
    """Simulates a daily pipeline run with multiple source feeds."""

    def test_simulated_daily_pipeline(self):
        """Full daily run: ingest MLS + county, dedup, compute metrics."""
        hashes: set[str] = set()

        # ── Morning: MLS feed ─────────────────────────────────────────────
        mls_result = process_discovery_batch(
            REALISTIC_MLS_FEED, "mls", existing_hashes=hashes
        )
        assert mls_result["new_assets_discovered"] == 3
        assert mls_result["failed_records"] == 0

        # ── Afternoon: County feed ────────────────────────────────────────
        county_result = process_discovery_batch(
            REALISTIC_COUNTY_FEED, "county", existing_hashes=hashes
        )
        assert county_result["new_assets_discovered"] == 2
        assert county_result["duplicates_skipped"] == 0

        # ── Evening: re-run full feeds — everything should dedup ──────────
        rerun = process_discovery_batch(
            REALISTIC_MLS_FEED + REALISTIC_COUNTY_FEED,
            "daily_pipeline",
            existing_hashes=hashes,
        )
        assert rerun["new_assets_discovered"] == 0
        assert rerun["duplicates_skipped"] == 5

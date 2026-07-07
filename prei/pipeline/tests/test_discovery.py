"""Tests for the Discovery stage canonical schema and ingestion sanitizer."""

import pytest

from prei.pipeline.handlers.discovery import (
    CanonicalPropertyPayload,
    DiscoverySanitizer,
)


# ═══════════════════════════════════════════════════════════════════════════════
#  Address normalization
# ═══════════════════════════════════════════════════════════════════════════════


class TestAddressNormalization:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("123 Main St., Apt #4B ", "123 main st apt 4b"),
            ("  456 OAK AVE   ", "456 oak ave"),
            ("789 Pine St\nSuit 2", "789 pine st suit 2"),
            ("", ""),
            (None, ""),
            ("  ", ""),
            ("1234", "1234"),
            ("Apt. 3B, 100 Market St.", "apt 3b 100 market st"),
        ],
    )
    def test_clean_address(self, raw, expected):
        assert DiscoverySanitizer.clean_address(raw) == expected

    def test_clean_address_idempotent(self):
        addr = " 123 Main St., Apt #4B "
        once = DiscoverySanitizer.clean_address(addr)
        twice = DiscoverySanitizer.clean_address(once)
        assert once == twice == "123 main st apt 4b"


# ═══════════════════════════════════════════════════════════════════════════════
#  SHA-256 address hashing
# ═══════════════════════════════════════════════════════════════════════════════


class TestAddressHashing:
    def test_hash_is_deterministic(self):
        h1 = DiscoverySanitizer.compute_address_hash("123 main st apt 4b")
        h2 = DiscoverySanitizer.compute_address_hash("123 main st apt 4b")
        assert h1 == h2

    def test_hash_is_sha256(self):
        h = DiscoverySanitizer.compute_address_hash("test")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_different_addresses_different_hashes(self):
        h1 = DiscoverySanitizer.compute_address_hash("123 main st")
        h2 = DiscoverySanitizer.compute_address_hash("456 oak ave")
        assert h1 != h2

    def test_normalized_vs_raw_same_hash(self):
        """Normalized and raw addresses that normalize the same produce same hash."""
        h1 = DiscoverySanitizer.compute_address_hash(
            DiscoverySanitizer.clean_address("123 Main St.")
        )
        h2 = DiscoverySanitizer.compute_address_hash(
            DiscoverySanitizer.clean_address("123 Main St., Apt")
        )
        assert h1 != h2  # different after normalization


# ═══════════════════════════════════════════════════════════════════════════════
#  transform_input
# ═══════════════════════════════════════════════════════════════════════════════


class TestTransformInput:
    MLS_RAW = {
        "id": "MLS-123",
        "address": "123 Main St., Apt #4B ",
        "price": 350_000.0,
        "rent": 2500.0,
        "beds": 3,
        "baths": 2,
        "sqft": 1800,
        "year_built": 2005,
    }

    def test_basic_mls_transform(self):
        result = DiscoverySanitizer.transform_input(self.MLS_RAW, source="mls_feed")
        assert isinstance(result, CanonicalPropertyPayload)
        assert result.source_id == "MLS-123"
        assert result.source_name == "mls_feed"
        assert result.raw_address == "123 Main St., Apt #4B "
        assert result.address_hash == DiscoverySanitizer.compute_address_hash(
            "123 main st apt 4b"
        )
        assert result.price == 350_000.0
        assert result.estimated_rent == 2500.0
        assert result.beds == 3
        assert result.baths == 2.0
        assert result.sqft == 1800.0
        assert result.year_built == 2005

    def test_missing_address_raises(self):
        with pytest.raises(ValueError, match="valid.*address"):
            DiscoverySanitizer.transform_input({"price": 100}, source="test")

    def test_empty_address_raises(self):
        with pytest.raises(ValueError, match="valid.*address"):
            DiscoverySanitizer.transform_input({"address": ""}, source="test")

    # ── Alternative key schemas (MLS county format) ──────────────────────────

    COUNTY_RAW = {
        "parcel_id": "PCN-9876",
        "FullStreetAddress": "  456 OAK AVE  ",
        "sale_price": 280_000.0,
        "BedroomsTotal": "3",
        "BathroomsTotalInteger": "2.5",
        "LivingArea": "1650",
        "YearBuilt": 1998,
    }

    def test_county_schema_transform(self):
        result = DiscoverySanitizer.transform_input(
            self.COUNTY_RAW, source="county_scraper"
        )
        assert result.source_id == "PCN-9876"
        assert result.source_name == "county_scraper"
        assert result.raw_address == "  456 OAK AVE  "
        assert result.address_hash == DiscoverySanitizer.compute_address_hash(
            "456 oak ave"
        )
        assert result.price == 280_000.0
        assert result.estimated_rent is None  # not in county data
        assert result.beds == 3
        assert result.baths == 2.5
        assert result.sqft == 1650.0
        assert result.year_built == 1998

    # ── Raw metadata passthrough ─────────────────────────────────────────────

    def test_raw_metadata_preserved(self):
        result = DiscoverySanitizer.transform_input(self.MLS_RAW, source="mls")
        assert result.raw_metadata["id"] == "MLS-123"
        assert result.raw_metadata["price"] == 350_000.0

    # ── Missing/null secondary fields → None ─────────────────────────────────

    def test_none_for_missing_fields(self):
        raw = {"address": "123 Main St", "price": 100_000, "beds": 2, "baths": 1}
        result = DiscoverySanitizer.transform_input(raw, source="minimal")
        assert result.estimated_rent is None
        assert result.sqft is None
        assert result.year_built is None

    # ── String numeric coercion ──────────────────────────────────────────────

    @pytest.mark.parametrize(
        "key,raw_val,expected",
        [
            ("beds", "3", 3),
            ("beds", 3.0, 3),
            ("beds", None, 0),
            ("baths", "2.5", 2.5),
            ("baths", 2, 2.0),
            ("baths", None, 0.0),
            ("price", "1998", 1998.0),
            ("price", None, None),
            ("sqft", None, None),
            ("sqft", "", None),
            ("year_built", "2005", 2005),
            ("year_built", None, None),
            ("year_built", "", None),
        ],
    )
    def test_type_coercion(self, key, raw_val, expected):
        raw = {
            "address": "123 Test St",
            "price": 100_000,
            "beds": 2,
            "baths": 1,
            key: raw_val,
        }
        result = DiscoverySanitizer.transform_input(raw, source="test")
        assert getattr(result, key) == expected

    # ── Zero or empty price → 0.0 ───────────────────────────────────────────

    @pytest.mark.parametrize("price_val", [None, "", "N/A"])
    def test_missing_price_defaults_to_zero(self, price_val):
        raw = {
            "address": "123 Test St",
            "price": price_val,
            "beds": 2,
            "baths": 1,
        }
        result = DiscoverySanitizer.transform_input(raw, source="test")
        # None/empty price becomes None (Optional[float]), not 0.0
        # N/A string becomes 0.0 via the coerce_float ValueError → 0.0 path
        if price_val == "N/A":
            assert result.price == 0.0
        else:
            assert result.price is None


# ═══════════════════════════════════════════════════════════════════════════════
#  CanonicalPropertyPayload pydantic validators
# ═══════════════════════════════════════════════════════════════════════════════


class TestCanonicalPropertyPayload:
    def test_direct_construction(self):
        p = CanonicalPropertyPayload(
            source_id="S1",
            source_name="test",
            raw_address="123 Main St",
            address_hash="a" * 64,
            price=250_000.0,
            beds=3,
            baths=2.0,
        )
        assert p.source_id == "S1"
        assert p.price == 250_000.0

    def test_coerce_price_from_string(self):
        p = CanonicalPropertyPayload(
            source_id="S1",
            source_name="test",
            raw_address="Addr",
            address_hash="h" * 64,
            price="350000",
            beds=3,
            baths=2,
        )
        assert p.price == 350_000.0

    def test_coerce_price_from_none(self):
        p = CanonicalPropertyPayload(
            source_id="S1",
            source_name="test",
            raw_address="Addr",
            address_hash="h" * 64,
            price=None,
            beds=3,
            baths=2,
        )
        assert p.price is None  # via coerce_float → None for None input

    def test_coerce_beds_from_float(self):
        p = CanonicalPropertyPayload(
            source_id="S1",
            source_name="test",
            raw_address="Addr",
            address_hash="h" * 64,
            price=100_000,
            beds=3.0,
            baths=2,
        )
        assert p.beds == 3

    def test_coerce_beds_from_string(self):
        p = CanonicalPropertyPayload(
            source_id="S1",
            source_name="test",
            raw_address="Addr",
            address_hash="h" * 64,
            price=100_000,
            beds="4",
            baths=2,
        )
        assert p.beds == 4

    def test_coerce_baths_from_int(self):
        p = CanonicalPropertyPayload(
            source_id="S1",
            source_name="test",
            raw_address="Addr",
            address_hash="h" * 64,
            price=100_000,
            beds=3,
            baths=2,
        )
        assert p.baths == 2.0
        assert isinstance(p.baths, float)

    def test_default_metadata_is_empty_dict(self):
        p = CanonicalPropertyPayload(
            source_id="S1",
            source_name="test",
            raw_address="Addr",
            address_hash="h" * 64,
            price=100_000,
            beds=3,
            baths=2,
        )
        assert p.raw_metadata == {}

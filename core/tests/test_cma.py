"""Unit tests for the CMA engine (core/services/cma.py).

Tests cover ``price_per_sqft`` and ``find_undervalued`` without requiring
database access — Listing instances are built in memory.

Phase 2.3 — CMA Engine Tests.
"""

from decimal import Decimal

from core.models import Listing
from core.services.cma import find_undervalued, price_per_sqft


def _listing(price: str, sq_ft: int) -> Listing:
    """Return an in-memory, unsaved Listing instance for testing without DB access."""
    return Listing(price=Decimal(price), sq_ft=sq_ft)


# ---------------------------------------------------------------------------
# price_per_sqft
# ---------------------------------------------------------------------------


def test_price_per_sqft_normal():
    """price=200000, sq_ft=1000 → Decimal('200.00')."""
    listing = _listing("200000", 1000)
    assert price_per_sqft(listing) == Decimal("200.00")


def test_price_per_sqft_zero_sq_ft():
    """sq_ft=0 → returns Decimal('0') without raising."""
    listing = _listing("200000", 0)
    assert price_per_sqft(listing) == Decimal("0")


def test_price_per_sqft_zero_price():
    """price=0 → returns Decimal('0')."""
    listing = _listing("0", 1000)
    assert price_per_sqft(listing) == Decimal("0")


def test_price_per_sqft_large_values():
    """Very large price with small sq_ft → no overflow; result is positive Decimal."""
    listing = _listing("9999999999.99", 1)
    result = price_per_sqft(listing)
    assert isinstance(result, Decimal)
    assert result > Decimal("0")


# ---------------------------------------------------------------------------
# find_undervalued
# ---------------------------------------------------------------------------


def test_find_undervalued_empty_list():
    """Empty listing list → returns empty."""
    assert list(find_undervalued([])) == []


def test_find_undervalued_all_same_ppsf():
    """All listings at the same PPSF → none returned (none below median × threshold)."""
    listings = [_listing("200000", 1000) for _ in range(4)]  # all PPSF = 200
    assert list(find_undervalued(listings)) == []


def test_find_undervalued_one_clearly_cheaper():
    """One listing clearly below the median PPSF → returned as undervalued."""
    cheap = _listing("50000", 1000)  # PPSF = 50
    normals = [_listing("200000", 1000) for _ in range(5)]  # PPSF = 200 each
    listings = [cheap] + normals

    result = list(find_undervalued(listings))

    assert len(result) == 1
    returned_listing, ppsf = result[0]
    assert returned_listing is cheap
    assert ppsf == Decimal("50")


def test_find_undervalued_custom_threshold():
    """threshold=0.5 → only listings with PPSF below half the median are returned."""
    # median PPSF = 100; cutoff = 100 * 0.5 = 50 → only PPSF=40 qualifies
    very_cheap = _listing("40000", 1000)  # PPSF = 40
    normals = [_listing("100000", 1000) for _ in range(3)]  # PPSF = 100 each
    listings = [very_cheap] + normals

    result = list(find_undervalued(listings, threshold=Decimal("0.5")))

    assert len(result) == 1
    assert result[0][0] is very_cheap


def test_find_undervalued_single_listing():
    """Single-listing input → returns empty list; a single listing is its own median and cannot be below threshold."""
    result = list(find_undervalued([_listing("200000", 1000)]))
    assert result == []


def test_find_undervalued_zero_sqft_excluded_no_crash():
    """Listings with sq_ft=0 are excluded from the median but don't cause a crash."""
    zero_sqft = _listing("200000", 0)  # excluded from ppsf computation
    cheap = _listing("50000", 1000)  # PPSF = 50
    normals = [_listing("200000", 1000) for _ in range(4)]  # PPSF = 200 each
    listings = [zero_sqft, cheap] + normals

    result = list(find_undervalued(listings))

    # cheap listing must be flagged; zero_sqft listing must not appear
    assert any(r[0] is cheap for r in result)
    assert not any(r[0] is zero_sqft for r in result)


def test_find_undervalued_ppsf_value_is_decimal():
    """Returned PPSF is a Decimal with the correct computed value."""
    cheap = _listing("100000", 1000)  # PPSF = 100
    normals = [_listing("200000", 1000) for _ in range(5)]  # PPSF = 200 each
    listings = [cheap] + normals

    result = list(find_undervalued(listings))

    assert len(result) == 1
    _, ppsf = result[0]
    assert isinstance(ppsf, Decimal)
    assert ppsf == Decimal("100")

"""Unit and integration tests for neighborhood-insights market adapters.

Covers:
- Unit tests for each adapter: comps, rents, crime, schools
- ``MarketSnapshot.__str__`` with zip-only and city/state variants
- ``refresh_market_snapshot`` happy-path (all adapters succeed)
- ``refresh_market_snapshot`` resilience (one adapter fails → error logged, snapshot saved)

Phase 2.2 — Neighborhood Insights: Market Adapter Integration Tests.

Live-network tests are marked ``@pytest.mark.integration`` and are skipped
by default (they would require real provider credentials/endpoints).
"""

import logging
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.utils import timezone

from core.integrations.market.comps import get_comps_for_listing
from core.integrations.market.crime import get_crime_score
from core.integrations.market.rents import get_rent_estimate_for_listing
from core.integrations.market.schools import get_school_rating
from core.models import Listing, MarketSnapshot
from core.services.market_data import refresh_market_snapshot

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_LISTING_DEFAULTS = dict(
    source="dummy",
    city="Austin",
    state="TX",
    zip_code="78701",
    price=Decimal("300000"),
    beds=3,
    baths=Decimal("2.0"),
    sq_ft=1500,
    property_type="SFH",
)


def _make_listing(
    *, address: str = "1 Main St", url: str = "https://example.com/1", **overrides
):
    """Create and return a test Listing instance."""
    return Listing.objects.create(
        address=address,
        url=url,
        posted_at=timezone.now(),
        **{**_LISTING_DEFAULTS, **overrides},
    )


def _assert_error_logged(caplog: pytest.LogCaptureFixture, *keywords: str) -> None:
    """Assert that at least one ERROR log record contains all *keywords* (case-insensitive)."""
    assert any(
        all(kw.lower() in record.message.lower() for kw in keywords)
        for record in caplog.records
        if record.levelno >= logging.ERROR
    ), (
        f"No ERROR log found containing all keywords {keywords!r}. Records: {[r.message for r in caplog.records]}"
    )


# ---------------------------------------------------------------------------
# comps adapter unit tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_comps_returns_three_items():
    """comps adapter returns exactly three comparable sales."""
    listing = _make_listing()
    comps = get_comps_for_listing(listing)
    assert len(comps) == 3


@pytest.mark.django_db
def test_comps_have_required_keys():
    """Each comp dict contains address, price, sq_ft and ppsf keys."""
    listing = _make_listing()
    comps = get_comps_for_listing(listing)
    for comp in comps:
        assert "address" in comp
        assert "price" in comp
        assert "sq_ft" in comp
        assert "ppsf" in comp


@pytest.mark.django_db
def test_comps_values_are_decimal():
    """comps adapter returns Decimal for price and ppsf fields."""
    listing = _make_listing()
    comps = get_comps_for_listing(listing)
    for comp in comps:
        assert isinstance(comp["price"], Decimal)
        assert isinstance(comp["ppsf"], Decimal)


@pytest.mark.django_db
def test_comps_zero_sqft_does_not_raise():
    """comps adapter handles zero sq_ft without raising."""
    listing = _make_listing(
        address="2 Zero Sq", url="https://example.com/zero", sq_ft=0
    )
    comps = get_comps_for_listing(listing)
    assert isinstance(comps, list)


# ---------------------------------------------------------------------------
# rents adapter unit tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_rents_returns_positive_decimal():
    """rents adapter returns a positive Decimal rent estimate for a valid listing."""
    listing = _make_listing()
    rent = get_rent_estimate_for_listing(listing)
    assert isinstance(rent, Decimal)
    assert rent > Decimal("0")


@pytest.mark.django_db
def test_rents_zero_sqft_returns_zero():
    """rents adapter returns Decimal('0') when sq_ft is zero."""
    listing = _make_listing(
        address="3 No Sqft", url="https://example.com/nosqft", sq_ft=0
    )
    rent = get_rent_estimate_for_listing(listing)
    assert rent == Decimal("0")


@pytest.mark.django_db
def test_rents_large_listing():
    """rents adapter scales correctly with a large price/sq_ft combination."""
    listing = _make_listing(
        address="4 Large",
        url="https://example.com/large",
        price=Decimal("2000000"),
        sq_ft=5000,
    )
    rent = get_rent_estimate_for_listing(listing)
    assert isinstance(rent, Decimal)
    assert rent > Decimal("0")


# ---------------------------------------------------------------------------
# crime adapter unit tests
# ---------------------------------------------------------------------------


def test_crime_score_texas():
    """crime adapter returns 2.5 for Texas."""
    score = get_crime_score(zip_code="78701", state="TX")
    assert score == Decimal("2.5")


def test_crime_score_california():
    """crime adapter returns 3.5 for California."""
    score = get_crime_score(zip_code="94110", state="CA")
    assert score == Decimal("3.5")


def test_crime_score_default_state():
    """crime adapter returns base score of 3.0 for an unknown state."""
    score = get_crime_score(zip_code="11111")
    assert score == Decimal("3.0")


def test_crime_score_no_args():
    """crime adapter handles all-None arguments without raising."""
    score = get_crime_score()
    assert isinstance(score, Decimal)


def test_crime_score_is_decimal():
    """crime adapter always returns a Decimal."""
    score = get_crime_score(zip_code="78701", city="Austin", state="TX")
    assert isinstance(score, Decimal)


# ---------------------------------------------------------------------------
# schools adapter unit tests
# ---------------------------------------------------------------------------


def test_school_rating_texas():
    """schools adapter returns 8.0 for Texas."""
    rating = get_school_rating(zip_code="78701", state="TX")
    assert rating == Decimal("8.0")


def test_school_rating_california():
    """schools adapter returns 7.0 for California."""
    rating = get_school_rating(zip_code="94110", state="CA")
    assert rating == Decimal("7.0")


def test_school_rating_default_state():
    """schools adapter returns 6.5 for an unknown state."""
    rating = get_school_rating(zip_code="11111")
    assert rating == Decimal("6.5")


def test_school_rating_no_args():
    """schools adapter handles all-None arguments without raising."""
    rating = get_school_rating()
    assert isinstance(rating, Decimal)


def test_school_rating_is_decimal():
    """schools adapter always returns a Decimal."""
    rating = get_school_rating(zip_code="78701", city="Austin", state="TX")
    assert isinstance(rating, Decimal)


# ---------------------------------------------------------------------------
# MarketSnapshot.__str__ tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_market_snapshot_str_zip_only():
    """__str__ includes the zip_code when city/state are empty."""
    snap = MarketSnapshot.objects.create(
        area_type="zip",
        zip_code="78701",
        rent_index=Decimal("1500"),
        price_trend=Decimal("0.10"),
        crime_score=Decimal("2.5"),
        school_rating=Decimal("8.0"),
    )
    assert "78701" in str(snap)


@pytest.mark.django_db
def test_market_snapshot_str_city_state_only():
    """__str__ includes city and state when zip_code is empty."""
    snap = MarketSnapshot.objects.create(
        area_type="city",
        zip_code="",
        city="Austin",
        state="TX",
        rent_index=Decimal("1500"),
        price_trend=Decimal("0.10"),
        crime_score=Decimal("2.5"),
        school_rating=Decimal("8.0"),
    )
    result = str(snap)
    assert "Austin" in result
    assert "TX" in result


# ---------------------------------------------------------------------------
# refresh_market_snapshot — all adapters succeed
# ---------------------------------------------------------------------------

_MOCK_COMPS = [
    {
        "address": "Comp 1",
        "price": Decimal("270000"),
        "sq_ft": 1500,
        "ppsf": Decimal("180.00"),
    },
    {
        "address": "Comp 2",
        "price": Decimal("300000"),
        "sq_ft": 1500,
        "ppsf": Decimal("200.00"),
    },
    {
        "address": "Comp 3",
        "price": Decimal("330000"),
        "sq_ft": 1500,
        "ppsf": Decimal("220.00"),
    },
]


@pytest.mark.django_db
def test_refresh_market_snapshot_all_succeed():
    """All adapters succeed → MarketSnapshot fields are populated."""
    _make_listing()

    with (
        patch(
            "core.services.market_data.get_crime_score", return_value=Decimal("2.5")
        ) as mock_crime,
        patch(
            "core.services.market_data.get_school_rating", return_value=Decimal("8.0")
        ) as mock_schools,
        patch(
            "core.services.market_data.get_rent_estimate_for_listing",
            return_value=Decimal("1500.00"),
        ) as mock_rents,
        patch(
            "core.services.market_data.get_comps_for_listing",
            return_value=_MOCK_COMPS,
        ) as mock_comps,
    ):
        snap = refresh_market_snapshot("78701")

    assert snap.zip_code == "78701"
    assert snap.crime_score == Decimal("2.5")
    assert snap.school_rating == Decimal("8.0")
    assert snap.rent_index == Decimal("1500.00")
    assert isinstance(snap.price_trend, Decimal)
    # Verify the snapshot was persisted
    assert MarketSnapshot.objects.filter(zip_code="78701").exists()
    mock_crime.assert_called_once_with(zip_code="78701")
    mock_schools.assert_called_once_with(zip_code="78701")
    mock_rents.assert_called_once()
    mock_comps.assert_called_once()


@pytest.mark.django_db
def test_refresh_market_snapshot_upserts_existing():
    """Calling refresh twice with the same zip_code upserts (not duplicates) the row."""
    _make_listing()

    with (
        patch("core.services.market_data.get_crime_score", return_value=Decimal("2.5")),
        patch(
            "core.services.market_data.get_school_rating", return_value=Decimal("8.0")
        ),
        patch(
            "core.services.market_data.get_rent_estimate_for_listing",
            return_value=Decimal("1500.00"),
        ),
        patch(
            "core.services.market_data.get_comps_for_listing", return_value=_MOCK_COMPS
        ),
    ):
        refresh_market_snapshot("78701")
        refresh_market_snapshot("78701")

    assert MarketSnapshot.objects.filter(zip_code="78701").count() == 1


@pytest.mark.django_db
def test_refresh_market_snapshot_no_listing_saves_crime_and_schools():
    """When no Listing exists for the ZIP, crime/school fields are still saved."""
    with (
        patch("core.services.market_data.get_crime_score", return_value=Decimal("3.0")),
        patch(
            "core.services.market_data.get_school_rating", return_value=Decimal("6.5")
        ),
        patch("core.services.market_data.get_rent_estimate_for_listing") as mock_rents,
        patch("core.services.market_data.get_comps_for_listing") as mock_comps,
    ):
        snap = refresh_market_snapshot("99999")

    assert snap.crime_score == Decimal("3.0")
    assert snap.school_rating == Decimal("6.5")
    assert snap.rent_index == Decimal("0")
    assert snap.price_trend == Decimal("0")
    # Adapters requiring a Listing should not have been called
    mock_rents.assert_not_called()
    mock_comps.assert_not_called()


# ---------------------------------------------------------------------------
# refresh_market_snapshot — one adapter fails
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_refresh_market_snapshot_crime_fails_logged(caplog):
    """crime adapter raises → error is logged; other fields still saved."""
    _make_listing()

    with caplog.at_level(logging.ERROR, logger="core.services.market_data"):
        with (
            patch(
                "core.services.market_data.get_crime_score",
                side_effect=Exception("network error"),
            ),
            patch(
                "core.services.market_data.get_school_rating",
                return_value=Decimal("8.0"),
            ),
            patch(
                "core.services.market_data.get_rent_estimate_for_listing",
                return_value=Decimal("1500.00"),
            ),
            patch(
                "core.services.market_data.get_comps_for_listing",
                return_value=_MOCK_COMPS,
            ),
        ):
            snap = refresh_market_snapshot("78701")

    assert snap.crime_score == Decimal("0")
    assert snap.school_rating == Decimal("8.0")
    assert snap.rent_index == Decimal("1500.00")
    assert MarketSnapshot.objects.filter(zip_code="78701").count() == 1
    _assert_error_logged(caplog, "get_crime_score")


@pytest.mark.django_db
def test_refresh_market_snapshot_schools_fails_logged(caplog):
    """schools adapter raises → error is logged; other fields still saved."""
    _make_listing()

    with caplog.at_level(logging.ERROR, logger="core.services.market_data"):
        with (
            patch(
                "core.services.market_data.get_crime_score", return_value=Decimal("2.5")
            ),
            patch(
                "core.services.market_data.get_school_rating",
                side_effect=Exception("timeout"),
            ),
            patch(
                "core.services.market_data.get_rent_estimate_for_listing",
                return_value=Decimal("1500.00"),
            ),
            patch(
                "core.services.market_data.get_comps_for_listing",
                return_value=_MOCK_COMPS,
            ),
        ):
            snap = refresh_market_snapshot("78701")

    assert snap.school_rating == Decimal("0")
    assert snap.crime_score == Decimal("2.5")
    assert MarketSnapshot.objects.filter(zip_code="78701").count() == 1
    _assert_error_logged(caplog, "school_rating adapter failed")


@pytest.mark.django_db
def test_refresh_market_snapshot_rents_fails_logged(caplog):
    """rents adapter raises → error is logged; rent_index defaults to zero."""
    _make_listing()

    with caplog.at_level(logging.ERROR, logger="core.services.market_data"):
        with (
            patch(
                "core.services.market_data.get_crime_score", return_value=Decimal("2.5")
            ),
            patch(
                "core.services.market_data.get_school_rating",
                return_value=Decimal("8.0"),
            ),
            patch(
                "core.services.market_data.get_rent_estimate_for_listing",
                side_effect=Exception("API down"),
            ),
            patch(
                "core.services.market_data.get_comps_for_listing",
                return_value=_MOCK_COMPS,
            ),
        ):
            snap = refresh_market_snapshot("78701")

    assert snap.rent_index == Decimal("0")
    assert snap.crime_score == Decimal("2.5")
    assert MarketSnapshot.objects.filter(zip_code="78701").count() == 1
    _assert_error_logged(caplog, "rent adapter failed")


@pytest.mark.django_db
def test_refresh_market_snapshot_comps_fails_logged(caplog):
    """comps adapter raises → error is logged; price_trend defaults to zero."""
    _make_listing()

    with caplog.at_level(logging.ERROR, logger="core.services.market_data"):
        with (
            patch(
                "core.services.market_data.get_crime_score", return_value=Decimal("2.5")
            ),
            patch(
                "core.services.market_data.get_school_rating",
                return_value=Decimal("8.0"),
            ),
            patch(
                "core.services.market_data.get_rent_estimate_for_listing",
                return_value=Decimal("1500.00"),
            ),
            patch(
                "core.services.market_data.get_comps_for_listing",
                side_effect=Exception("comps unavailable"),
            ),
        ):
            snap = refresh_market_snapshot("78701")

    assert snap.price_trend == Decimal("0")
    assert snap.rent_index == Decimal("1500.00")
    assert MarketSnapshot.objects.filter(zip_code="78701").count() == 1
    _assert_error_logged(caplog, "fetch_comps_for_listing failed")

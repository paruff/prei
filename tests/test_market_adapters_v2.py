"""Tests for market data adapters (TASK-A2 through TASK-A5).

Covers:
  - fetch_comps_for_listing  (TASK-A3)
  - refresh_market_snapshot rent/school wiring (TASK-A4)
  - refresh_market_snapshot crime/comps wiring (TASK-A5)

All HTTP calls are mocked — no real API calls in CI.
The ``data_source`` field on ``MarketSnapshot`` is validated to distinguish
real vs. dummy-sourced rows (TASK-A5 requirement).
"""

from __future__ import annotations

import os
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.utils import timezone

from core.integrations.market.comps import fetch_comps_for_listing
from core.models import Listing, MarketSnapshot


# ===========================================================================
#  TASK-A3 — comps.py adapter (fetch_comps_for_listing)
# ===========================================================================


class CompsFetchCompsForListingTest(TestCase):
    """Test the ATTOM-backed comps adapter."""

    def setUp(self):
        now = timezone.now()
        self.listing = Listing.objects.create(
            source="dummy",
            address="123 Main St",
            city="Austin",
            state="TX",
            zip_code="78701",
            price=Decimal("300000"),
            sq_ft=1500,
            url="https://example.com/listing/1",
            posted_at=now,
        )

    # --- missing key ---

    @patch("core.integrations.market.comps.ATTOMAdapter")
    def test_returns_empty_on_missing_key(self, mock_adapter_cls):
        """Returns empty list when ATTOM_API_KEY not set."""
        with patch.dict(os.environ, {}, clear=True):
            result = fetch_comps_for_listing(self.listing, api_key="")
        self.assertEqual(result, [])
        mock_adapter_cls.assert_not_called()

    # --- HTTP / API failure ---

    @patch("core.integrations.market.comps.ATTOMAdapter")
    def test_returns_empty_on_api_error(self, mock_adapter_cls):
        """Returns empty list when ATTOM raises APIError."""
        mock_adapter = MagicMock()
        mock_adapter_cls.return_value = mock_adapter
        from core.integrations.sources.attom_adapter import ATTOMAPIError

        mock_adapter.fetch_sales_history.side_effect = ATTOMAPIError("API fault")

        with patch.dict(os.environ, {"ATTOM_API_KEY": "test-key"}):
            result = fetch_comps_for_listing(self.listing)

        self.assertEqual(result, [])

    # --- empty response ---

    @patch("core.integrations.market.comps.ATTOMAdapter")
    def test_returns_empty_on_no_sales(self, mock_adapter_cls):
        """Returns empty list when ATTOM returns no sale history."""
        mock_adapter = MagicMock()
        mock_adapter_cls.return_value = mock_adapter
        mock_adapter.fetch_sales_history.return_value = {"property": []}

        with patch.dict(os.environ, {"ATTOM_API_KEY": "test-key"}):
            result = fetch_comps_for_listing(self.listing)

        self.assertEqual(result, [])

    # --- successful response ---

    @patch("core.integrations.market.comps.ATTOMAdapter")
    def test_returns_comps_on_success(self, mock_adapter_cls):
        """Returns list of comp dicts on successful ATTOM response."""
        mock_adapter = MagicMock()
        mock_adapter_cls.return_value = mock_adapter
        sales_response = {
            "property": [
                {
                    "saleHistory": [
                        {
                            "amount": {"saleAmt": 295000},
                            "lotSize2": 1400,
                        },
                        {
                            "amount": {"saleAmt": 310000},
                            "lotSize2": 1550,
                        },
                    ]
                }
            ]
        }
        mock_adapter.fetch_sales_history.return_value = sales_response

        with patch.dict(os.environ, {"ATTOM_API_KEY": "test-key"}):
            result = fetch_comps_for_listing(self.listing)

        self.assertEqual(len(result), 2)
        for comp in result:
            self.assertIn("address", comp)
            self.assertIn("price", comp)
            self.assertIn("sq_ft", comp)
            self.assertIn("ppsf", comp)
            self.assertIsInstance(comp["price"], Decimal)
            self.assertIsInstance(comp["ppsf"], Decimal)
        # Check first comp
        self.assertEqual(result[0]["sq_ft"], 1400)
        self.assertEqual(result[0]["price"], Decimal("295000.00"))


# ===========================================================================
#  TASK-A4 — refresh_market_snapshot rent/school wiring
# ===========================================================================


class MarketDataRentSchoolWiringTest(TestCase):
    """Test that refresh_market_snapshot wires rent + school correctly."""

    def setUp(self):
        now = timezone.now()
        self.listing = Listing.objects.create(
            source="dummy",
            address="456 Oak Ave",
            city="Portland",
            state="OR",
            zip_code="97201",
            price=Decimal("400000"),
            sq_ft=1800,
            url="https://example.com/listing/2",
            posted_at=now,
        )

    # --- rent: key present, API returns value ---

    @patch("core.services.market_data.fetch_rent_estimate")
    @patch("core.services.market_data.fetch_school_rating")
    def test_rent_uses_live_when_key_and_data(self, mock_school, mock_rent):
        """Uses fetch_rent_estimate result when API returns a value."""
        mock_rent.return_value = Decimal("2200.00")
        mock_school.return_value = Decimal("7.5")

        keys = {"RENTCAST_API_KEY": "rc-key", "GREATSCHOOLS_API_KEY": "gs-key"}
        with patch.dict(os.environ, keys):
            snap = MarketDataServiceHelper.refresh("97201")

        self.assertEqual(snap.rent_index, Decimal("2200.00"))
        self.assertEqual(snap.school_rating, Decimal("7.5"))
        self.assertIn("rentcast", snap.data_source)

    # --- rent: key present but API returns None -> dummy fallback ---

    @patch("core.services.market_data.fetch_rent_estimate")
    @patch("core.services.market_data.fetch_school_rating")
    @patch("core.services.market_data.get_rent_estimate_for_listing")
    def test_rent_falls_back_when_api_returns_none(
        self, mock_dummy_rent, mock_school, mock_rent
    ):
        """Falls back to dummy rent when fetch_rent_estimate returns None."""
        mock_rent.return_value = None
        mock_dummy_rent.return_value = Decimal("1800.00")
        mock_school.return_value = Decimal("7.5")

        keys = {"RENTCAST_API_KEY": "rc-key", "GREATSCHOOLS_API_KEY": "gs-key"}
        with patch.dict(os.environ, keys):
            snap = MarketDataServiceHelper.refresh("97201")

        self.assertEqual(snap.rent_index, Decimal("1800.00"))
        mock_dummy_rent.assert_called_once()

    # --- school: key absent -> dummy fallback ---

    @patch("core.services.market_data.fetch_rent_estimate")
    @patch("core.services.market_data.fetch_school_rating")
    @patch("core.services.market_data.get_school_rating")
    def test_school_uses_dummy_when_key_missing(
        self, mock_dummy_school, mock_school, mock_rent
    ):
        """Falls back to dummy school when key not set."""
        mock_rent.return_value = Decimal("2000.00")
        mock_school.return_value = None
        mock_dummy_school.return_value = Decimal("7.5")

        keys = {"RENTCAST_API_KEY": "rc-key"}  # no GREATSCHOOLS_API_KEY
        with patch.dict(os.environ, keys):
            snap = MarketDataServiceHelper.refresh("97201")

        self.assertEqual(snap.school_rating, Decimal("7.5"))
        mock_school.assert_not_called()  # fetch_school_rating not called at all
        mock_dummy_school.assert_called_once()

    # --- rent: key absent -> dummy fallback ---

    @patch("core.services.market_data.fetch_rent_estimate")
    @patch("core.services.market_data.fetch_school_rating")
    @patch("core.services.market_data.get_rent_estimate_for_listing")
    def test_rent_uses_dummy_when_key_missing(
        self, mock_dummy_rent, mock_school, mock_rent
    ):
        """Falls back to dummy rent when key not set."""
        mock_rent.return_value = None
        mock_dummy_rent.return_value = Decimal("1600.00")
        mock_school.return_value = Decimal("6.0")

        keys = {"GREATSCHOOLS_API_KEY": "gs-key"}  # no RENTCAST_API_KEY
        with patch.dict(os.environ, keys):
            snap = MarketDataServiceHelper.refresh("97201")

        self.assertEqual(snap.rent_index, Decimal("1600.00"))
        mock_rent.assert_not_called()  # fetch_rent_estimate not called at all
        mock_dummy_rent.assert_called_once()


# ===========================================================================
#  TASK-A5 — refresh_market_snapshot crime/comps wiring + data_source
# ===========================================================================


class MarketDataCrimeCompsWiringTest(TestCase):
    """Test that refresh_market_snapshot wires crime + comps correctly."""

    def setUp(self):
        now = timezone.now()
        self.listing = Listing.objects.create(
            source="dummy",
            address="789 Pine St",
            city="Denver",
            state="CO",
            zip_code="80202",
            price=Decimal("500000"),
            sq_ft=2000,
            url="https://example.com/listing/3",
            posted_at=now,
        )

    # --- crime is always dummy (per TASK-A1/DECISION-2 Option C) ---

    @patch("core.services.market_data.fetch_rent_estimate")
    @patch("core.services.market_data.fetch_school_rating")
    def test_crime_is_always_dummy(self, mock_school, mock_rent):
        """Crime score always comes from dummy get_crime_score."""
        mock_rent.return_value = Decimal("2500.00")
        mock_school.return_value = Decimal("8.0")

        keys = {"RENTCAST_API_KEY": "rc-key", "GREATSCHOOLS_API_KEY": "gs-key"}
        with patch.dict(os.environ, keys):
            snap = MarketDataServiceHelper.refresh("80202")

        # Default dummy crime for non-TX/non-CA is Decimal("3.0")
        self.assertEqual(snap.crime_score, Decimal("3.0"))
        # data_source should not contain any crime adapter tag
        self.assertNotIn("crime", snap.data_source)

    # --- comps: live ATTOM -> returns list ---

    @patch("core.services.market_data.fetch_comps_for_listing")
    @patch("core.services.market_data.fetch_rent_estimate")
    @patch("core.services.market_data.fetch_school_rating")
    def test_comps_uses_live_when_attom_returns_data(
        self, mock_school, mock_rent, mock_comps
    ):
        """Uses fetch_comps_for_listing when it returns data."""
        mock_rent.return_value = Decimal("2000.00")
        mock_school.return_value = Decimal("7.0")
        mock_comps.return_value = [
            {
                "address": "Comp 1",
                "price": Decimal("510000"),
                "sq_ft": 2000,
                "ppsf": Decimal("255.00"),
            },
            {
                "address": "Comp 2",
                "price": Decimal("490000"),
                "sq_ft": 1950,
                "ppsf": Decimal("251.28"),
            },
        ]

        with patch.dict(
            os.environ,
            {
                "RENTCAST_API_KEY": "rk",
                "GREATSCHOOLS_API_KEY": "gk",
                "ATTOM_API_KEY": "ak",
            },
        ):
            snap = MarketDataServiceHelper.refresh("80202")

        self.assertIn("attom", snap.data_source)
        # price_trend should be computed from comps: avg ~500000 vs listing 500000 -> 0
        self.assertEqual(snap.price_trend, Decimal("0.0000"))

    # --- comps: live ATTOM returns empty -> dummy fallback ---

    @patch("core.services.market_data.fetch_comps_for_listing")
    @patch("core.services.market_data.get_comps_for_listing")
    @patch("core.services.market_data.fetch_rent_estimate")
    @patch("core.services.market_data.fetch_school_rating")
    def test_comps_falls_back_when_attom_empty(
        self, mock_school, mock_rent, mock_dummy_comps, mock_comps
    ):
        """Falls back to dummy comps when fetch_comps_for_listing returns empty."""
        mock_rent.return_value = Decimal("2000.00")
        mock_school.return_value = Decimal("7.0")
        mock_comps.return_value = []
        mock_dummy_comps.return_value = [
            {
                "address": "Dummy Comp",
                "price": Decimal("500000"),
                "sq_ft": 2000,
                "ppsf": Decimal("250.00"),
            },
        ]

        keys = {
            "RENTCAST_API_KEY": "rk",
            "GREATSCHOOLS_API_KEY": "gk",
            "ATTOM_API_KEY": "ak",
        }
        with patch.dict(os.environ, keys):
            snap = MarketDataServiceHelper.refresh("80202")

        self.assertNotIn("attom", snap.data_source)
        mock_dummy_comps.assert_called_once()

    # --- data_source reflects full-dummy snapshot ---

    @patch("core.services.market_data.fetch_rent_estimate")
    @patch("core.services.market_data.fetch_school_rating")
    @patch("core.services.market_data.fetch_comps_for_listing")
    def test_data_source_dummy_when_no_keys(self, mock_comps, mock_school, mock_rent):
        """data_source is 'dummy' when no API keys are set."""
        mock_rent.return_value = None
        mock_school.return_value = None
        mock_comps.return_value = []

        with patch.dict(os.environ, {}, clear=True):
            snap = MarketDataServiceHelper.refresh("80202")

        self.assertEqual(snap.data_source, "dummy")


# ===========================================================================
#  Helper: wraps refresh_market_snapshot with required mocks
# ===========================================================================


class MarketDataServiceHelper:
    """Convenience wrapper to call refresh_market_snapshot with mocks.

    The service calls get_crime_score which we do NOT mock (it's pure
    deterministic dummy logic — no external calls).  All other adapters
    are mocked by the individual test decorators.
    """

    @staticmethod
    def refresh(zip_code: str) -> MarketSnapshot:
        # Import here to avoid module-level side effects in test discovery.
        from core.services.market_data import refresh_market_snapshot

        return refresh_market_snapshot(zip_code)

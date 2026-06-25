"""Unit tests for market data API adapters (v2)."""

import hashlib
import json
from datetime import date
from decimal import Decimal
from unittest.mock import patch, MagicMock

import requests
from django.core.cache import cache
from django.test import TestCase

from core.integrations.market.rents import fetch_rent_estimate
from core.integrations.market.schools import fetch_school_rating
from core.integrations.market.walkscore import fetch_walk_score


class RentCastFetchRentEstimateTest(TestCase):
    def setUp(self):
        cache.clear()

    @patch("core.integrations.market.rents.requests.get")
    def test_returns_decimal_on_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": {"rent": 1850.00}}
        mock_get.return_value = mock_resp
        result = fetch_rent_estimate("123 Main St", "test-key")
        assert result == Decimal("1850.00")

    @patch("core.integrations.market.rents.requests.get")
    def test_returns_none_on_empty_api_key(self, mock_get):
        result = fetch_rent_estimate("123 Main St", "")
        assert result is None
        mock_get.assert_not_called()

    @patch("core.integrations.market.rents.requests.get")
    def test_returns_none_on_http_error(self, mock_get):
        mock_get.side_effect = requests.exceptions.HTTPError()
        result = fetch_rent_estimate("123 Main St", "test-key")
        assert result is None

    @patch("core.integrations.market.rents.requests.get")
    def test_returns_none_on_connection_error(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError()
        result = fetch_rent_estimate("123 Main St", "test-key")
        assert result is None

    @patch("core.integrations.market.rents.requests.get")
    def test_returns_none_on_invalid_json(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.side_effect = json.JSONDecodeError("", "", 0)
        mock_get.return_value = mock_resp
        result = fetch_rent_estimate("123 Main St", "test-key")
        assert result is None

    @patch("core.integrations.market.rents.requests.get")
    def test_returns_none_on_missing_key(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": {}}
        mock_get.return_value = mock_resp
        result = fetch_rent_estimate("123 Main St", "test-key")
        assert result is None

    @patch("core.integrations.market.rents.requests.get")
    def test_returns_none_on_budget_exceeded(self, mock_get):
        today = date.today().isoformat()
        cache.set(f"rentcast_calls_{today}", 100, timeout=86400)
        result = fetch_rent_estimate("123 Main St", "test-key")
        assert result is None
        mock_get.assert_not_called()

    @patch("core.integrations.market.rents.requests.get")
    def test_cache_hit_returns_cached(self, mock_get):
        address = "123 Main St"
        cache_key = f"rentcast_rent_{hashlib.md5(address.encode()).hexdigest()}"
        cache.set(cache_key, Decimal("1700"))
        result = fetch_rent_estimate(address, "test-key")
        assert result == Decimal("1700")
        mock_get.assert_not_called()

    @patch("core.integrations.market.rents.cache.set")
    @patch("core.integrations.market.rents.requests.get")
    def test_cache_set_on_success(self, mock_get, mock_cache_set):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": {"rent": 1850.00}}
        mock_get.return_value = mock_resp
        address = "123 Main St"
        fetch_rent_estimate(address, "test-key")
        expected_key = f"rentcast_rent_{hashlib.md5(address.encode()).hexdigest()}"
        mock_cache_set.assert_any_call(expected_key, Decimal("1850.00"), timeout=604800)


class GreatSchoolsFetchSchoolRatingTest(TestCase):
    def setUp(self):
        cache.clear()

    @patch("core.integrations.market.schools.requests.get")
    def test_returns_decimal_average(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"gsRating": "7"}, {"gsRating": "9"}]
        mock_get.return_value = mock_resp
        result = fetch_school_rating("12345", "test-key")
        assert result == Decimal("8.0")

    @patch("core.integrations.market.schools.requests.get")
    def test_returns_none_on_empty_api_key(self, mock_get):
        result = fetch_school_rating("12345", "")
        assert result is None
        mock_get.assert_not_called()

    @patch("core.integrations.market.schools.requests.get")
    def test_returns_none_on_http_error(self, mock_get):
        mock_get.side_effect = requests.exceptions.HTTPError()
        result = fetch_school_rating("12345", "test-key")
        assert result is None

    @patch("core.integrations.market.schools.requests.get")
    def test_cache_hit_returns_cached(self, mock_get):
        cache_key = "greatschools_rating_12345"
        cache.set(cache_key, Decimal("7.5"))
        result = fetch_school_rating("12345", "test-key")
        assert result == Decimal("7.5")
        mock_get.assert_not_called()

    @patch("core.integrations.market.schools.cache.set")
    @patch("core.integrations.market.schools.requests.get")
    def test_cache_set_on_success(self, mock_get, mock_cache_set):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"gsRating": "8"}]
        mock_get.return_value = mock_resp
        fetch_school_rating("12345", "test-key")
        mock_cache_set.assert_any_call(
            "greatschools_rating_12345", Decimal("8.0"), timeout=2592000
        )

    @patch("core.integrations.market.schools.requests.get")
    def test_returns_none_on_empty_list(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = []
        mock_get.return_value = mock_resp
        result = fetch_school_rating("12345", "test-key")
        assert result is None

    @patch("core.integrations.market.schools.requests.get")
    def test_returns_decimal_precision(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"gsRating": "7.3"}, {"gsRating": "8.7"}]
        mock_get.return_value = mock_resp
        result = fetch_school_rating("12345", "test-key")
        assert result == Decimal("8.0")


class WalkScoreFetchWalkScoreTest(TestCase):
    def setUp(self):
        cache.clear()

    @patch("core.integrations.market.walkscore.requests.get")
    def test_returns_dict_with_all_scores(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "walkscore": 89,
            "transit": {"score": 72},
            "bike": {"score": 85},
        }
        mock_get.return_value = mock_resp
        result = fetch_walk_score("123 Main St", "test-key")
        assert isinstance(result["walk_score"], int)
        assert isinstance(result["transit_score"], int)
        assert isinstance(result["bike_score"], int)
        assert result["walk_score"] == 89
        assert result["transit_score"] == 72
        assert result["bike_score"] == 85

    @patch("core.integrations.market.walkscore.requests.get")
    def test_transit_and_bike_optional(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"walkscore": 50}
        mock_get.return_value = mock_resp
        result = fetch_walk_score("123 Main St", "test-key")
        assert result["walk_score"] == 50
        assert result["transit_score"] is None
        assert result["bike_score"] is None

    @patch("core.integrations.market.walkscore.requests.get")
    def test_returns_none_on_empty_api_key(self, mock_get):
        result = fetch_walk_score("123 Main St", "")
        assert result is None
        mock_get.assert_not_called()

    @patch("core.integrations.market.walkscore.requests.get")
    def test_returns_none_on_http_error(self, mock_get):
        mock_get.side_effect = requests.exceptions.HTTPError()
        result = fetch_walk_score("123 Main St", "test-key")
        assert result is None

    @patch("core.integrations.market.walkscore.requests.get")
    def test_cache_hit_returns_cached(self, mock_get):
        address = "123 Main St"
        cache_key = f"walkscore_{hashlib.md5(address.encode()).hexdigest()}"
        cache.set(
            cache_key, {"walk_score": 95, "transit_score": None, "bike_score": None}
        )
        result = fetch_walk_score(address, "test-key")
        assert result["walk_score"] == 95
        mock_get.assert_not_called()

    @patch("core.integrations.market.walkscore.cache.set")
    @patch("core.integrations.market.walkscore.requests.get")
    def test_cache_set_on_success(self, mock_get, mock_cache_set):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"walkscore": 89}
        mock_get.return_value = mock_resp
        address = "123 Main St"
        fetch_walk_score(address, "test-key")
        expected_key = f"walkscore_{hashlib.md5(address.encode()).hexdigest()}"
        mock_cache_set.assert_any_call(
            expected_key,
            {"walk_score": 89, "transit_score": None, "bike_score": None},
            timeout=2592000,
        )

    @patch("core.integrations.market.walkscore.requests.get")
    def test_returns_none_on_missing_walkscore(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"status": 2}
        mock_get.return_value = mock_resp
        result = fetch_walk_score("123 Main St", "test-key")
        assert result is None

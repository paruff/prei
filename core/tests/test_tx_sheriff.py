"""Tests for the Texas county sheriff sale scraper (core/integrations/county/tx_sheriff.py)."""

from __future__ import annotations

from unittest.mock import patch

from core.integrations.county.tx_sheriff import (
    SHERIFF_COUNTIES,
    scrape_all_sheriff_sales,
    scrape_sheriff_sales,
)


class TestSheriffConstants:
    """SHERIFF_COUNTIES data integrity checks."""

    def test_has_known_counties(self) -> None:
        names = {c["county_name"] for c in SHERIFF_COUNTIES}
        assert "Harris" in names
        assert "Dallas" in names
        assert "Travis" in names
        assert "Bexar" in names
        assert "Tarrant" in names

    def test_each_county_has_endpoint(self) -> None:
        for c in SHERIFF_COUNTIES:
            assert c["endpoint"].startswith("https://")

    def test_each_county_has_selectors(self) -> None:
        for c in SHERIFF_COUNTIES:
            assert "table" in c["selectors"]
            assert "alt_tables" in c["selectors"]


class TestScrapeSheriffSales:
    """Tests for scrape_sheriff_sales with mocked Playwright."""

    def test_returns_list_for_known_county(self) -> None:
        """A known county name calls the base scraper."""
        with patch(
            "core.integrations.county.tx_sheriff.scrape_county_nts",
            return_value=[{"address": "123 Main"}],
        ):
            result = scrape_sheriff_sales("Harris")
            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0]["address"] == "123 Main"

    def test_case_insensitive_county_match(self) -> None:
        """County name matching should be case-insensitive."""
        with patch(
            "core.integrations.county.tx_sheriff.scrape_county_nts",
            return_value=[{"address": "456 Oak"}],
        ):
            result = scrape_sheriff_sales("harris")
            assert len(result) == 1

    def test_unknown_county_returns_empty_list(self) -> None:
        """An unknown county name returns [] without calling the base scraper."""
        with patch(
            "core.integrations.county.tx_sheriff.scrape_county_nts",
        ) as mock_base:
            result = scrape_sheriff_sales("Nonexistent")
            assert result == []
            mock_base.assert_not_called()

    def test_logs_warning_for_unknown_county(self, caplog) -> None:
        """A warning is logged when no config is found."""
        import logging

        caplog.set_level(logging.WARNING)
        scrape_sheriff_sales("UnknownCounty")
        assert "no config for UnknownCounty" in caplog.text


class TestScrapeAllSheriffSales:
    """Tests for scrape_all_sheriff_sales."""

    def test_returns_dict_with_all_counties(self) -> None:
        """Returns a dict keyed by county name."""
        with patch(
            "core.integrations.county.tx_sheriff.scrape_county_nts",
            return_value=[{"address": "789 Pine"}],
        ):
            result = scrape_all_sheriff_sales()
            assert isinstance(result, dict)
            for c in SHERIFF_COUNTIES:
                assert c["county_name"] in result

"""FRED (Federal Reserve Economic Data) API adapter for economic indicators.

Provides access to housing permits, housing starts, population, employment,
and other economic series useful for supply-constraint analysis and growth
area evaluation.

API docs: https://fred.stlouisfed.org/docs/api/fred/
"""

from __future__ import annotations

import logging
import os
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, cast

import requests

logger = logging.getLogger(__name__)

FRED_API_BASE = "https://api.stlouisfed.org/fred"


class FREDAPIError(Exception):
    """Base exception for FRED API errors."""

    pass


class FREDAuthenticationError(FREDAPIError):
    """Authentication failed with FRED API."""

    pass


class FREDAdapter:
    """
    Adapter for FRED API.

    Provides access to economic time series data relevant to real estate
    investment analysis, particularly building permits and housing starts
    for supply-constraint evaluation.
    """

    CACHE_DURATION = 86400  # 24 hours

    # Key FRED series for supply constraint analysis
    SERIES = {
        # Building permits - national
        "permits_us": "PERMIT",
        # Building permits by state (seasonally adjusted) - format: {STATE}BPPRIVSA
        # Housing starts - national
        "starts_us": "HOUST",
        # Housing starts by region
        "starts_ne": "HOUSTNE",
        "starts_mw": "HOUSTMW",
        "starts_south": "HOUSTS",
        "starts_west": "HOUSTW",
        # Total housing units authorized by building permits
        "permits_1unit": "PERMIT1",
        "permits_5plus": "PERMIT5",
        # Population (annual)
        "population_us": "POPTHM",
        # Civilian labor force
        "labor_force": "CLF16OV",
        # Unemployment rate
        "unemployment": "UNRATE",
        # Median household income
        "median_income": "MEHOINUSA672N",
        # 30-year mortgage rate
        "mortgage_30yr": "MORTGAGE30US",
        # Federal funds rate
        "fed_funds": "FEDFUNDS",
    }

    # State building permit series (seasonally adjusted)
    STATE_PERMIT_SERIES = {
        "CA": "CABPPRIVSA",
        "TX": "TXBPPRIVSA",
        "FL": "FLBPPRIVSA",
        "NY": "NYBPPRIVSA",
        "IL": "ILBPPRIVSA",
        "PA": "PABPPRIVSA",
        "OH": "OHBPPRIVSA",
        "GA": "GABPPRIVSA",
        "NC": "NCBPPRIVSA",
        "MI": "MIBPPRIVSA",
    }

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize FRED API adapter.

        Args:
            api_key: FRED API key (free registration at fred.stlouisfed.org).
                     If None, reads from FRED_API_KEY or FRED_api_key environment variable.
        """
        self.api_key = (
            api_key or os.getenv("FRED_API_KEY") or os.getenv("FRED_api_key", "")
        )
        if not self.api_key:
            logger.warning("FRED API key not configured")

        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
            }
        )

    def _make_request(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute FRED API request with error handling."""
        if not self.api_key:
            raise FREDAuthenticationError("FRED API key not configured")

        if params is None:
            params = {}

        params["api_key"] = self.api_key
        params["file_type"] = "json"

        url = f"{FRED_API_BASE}{endpoint}"

        try:
            resp = self.session.get(url, params=params, timeout=15)
            resp.raise_for_status()
        except requests.exceptions.HTTPError as exc:
            # FRED returns 400 for both invalid keys and invalid series
            # Check response body for error details to distinguish
            if exc.response is not None:
                try:
                    error_data = exc.response.json()
                    error_msg = error_data.get("error_message", "").lower()
                    if (
                        "api_key" in error_msg
                        or "api key" in error_msg
                        or "invalid" in error_msg
                    ):
                        logger.error("FRED API authentication failed")
                        raise FREDAuthenticationError("Invalid FRED API key")
                    if "not found" in error_msg or "no series" in error_msg:
                        logger.warning(
                            "FRED series not found: %s",
                            params.get("series_id", "unknown"),
                        )
                        # Return empty result instead of raising for not-found series
                        return {"seriess": [], "observations": []}
                except ValueError:
                    pass  # Not JSON, fall through to generic error

            if exc.response is not None and exc.response.status_code == 401:
                logger.error("FRED API authentication failed")
                raise FREDAuthenticationError("Invalid FRED API key")
            logger.error("FRED API HTTP error: %s", exc)
            raise FREDAPIError(f"API request failed: {exc}")
        except requests.exceptions.RequestException as exc:
            logger.error("FRED API request failed: %s", exc)
            raise FREDAPIError(f"Request failed: {exc}")

        try:
            result: Dict[str, Any] = resp.json()
            return result
        except ValueError as exc:
            logger.error("FRED API returned invalid JSON: %s", exc)
            raise FREDAPIError("Invalid JSON response")

    def get_series_observations(
        self,
        series_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        frequency: Optional[str] = None,
        units: Optional[str] = None,
        limit: Optional[int] = None,
        sort_order: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get observations for a FRED series.

        Args:
            series_id: FRED series ID (e.g., "PERMIT", "HOUST")
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            frequency: Frequency to aggregate to (e.g., "m" monthly, "q" quarterly, "a" annual)
            units: Units transformation (e.g., "lin" linear, "chg" change, "pch" percent change)
            limit: Maximum number of observations to return
            sort_order: Sort order ("asc" or "desc")

        Returns:
            List of observation dicts with "date" and "value" keys
        """
        params: Dict[str, Any] = {"series_id": series_id}
        if start_date:
            params["observation_start"] = start_date
        if end_date:
            params["observation_end"] = end_date
        if frequency:
            params["frequency"] = frequency
        if units:
            params["units"] = units
        if limit:
            params["limit"] = limit
        if sort_order:
            params["sort_order"] = sort_order

        data = self._make_request("/series/observations", params)
        return cast(List[Dict[str, Any]], data.get("observations", []))

    def get_latest_observation(self, series_id: str) -> Optional[Dict[str, Any]]:
        """Get the most recent observation for a series."""
        obs = self.get_series_observations(series_id, limit=1, sort_order="desc")
        return obs[0] if obs else None

    def get_series_info(self, series_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata about a FRED series."""
        data = self._make_request("/series", {"series_id": series_id})
        series = data.get("seriess", [])
        return series[0] if series else None

    def get_category_series(self, category_id: int) -> List[Dict[str, Any]]:
        """Get series IDs in a FRED category."""
        data = self._make_request("/category/series", {"category_id": category_id})
        return cast(List[Dict[str, Any]], data.get("seriess", []))

    def search_series(
        self,
        search_text: str,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Search FRED series by text."""
        data = self._make_request(
            "/series/search", {"search_text": search_text, "limit": limit}
        )
        return cast(List[Dict[str, Any]], data.get("seriess", []))

    # Convenience methods for key supply-constraint indicators

    def get_building_permits(
        self,
        state_code: Optional[str] = None,
        start_date: Optional[str] = None,
        frequency: str = "m",
        limit: Optional[int] = None,
        sort_order: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get building permits data.

        Args:
            state_code: 2-letter state code (e.g., "CA") for state-level permits.
                       If None, returns national PERMIT series.
            start_date: Start date for observations
            frequency: Frequency ("m" monthly, "q" quarterly, "a" annual)
            limit: Maximum number of observations to return
            sort_order: Sort order ("asc" or "desc")

        Returns:
            List of observations with date and value
        """
        if state_code:
            state_code = state_code.upper()
            series_id = self.STATE_PERMIT_SERIES.get(state_code)
            if not series_id:
                logger.warning(
                    f"No FRED building permit series found for state: {state_code}"
                )
                return []
        else:
            series_id = self.SERIES["permits_us"]

        return self.get_series_observations(
            series_id=series_id,
            start_date=start_date,
            frequency=frequency,
            limit=limit,
            sort_order=sort_order,
        )

    def get_housing_starts(
        self,
        region: Optional[str] = None,
        start_date: Optional[str] = None,
        frequency: str = "m",
        limit: Optional[int] = None,
        sort_order: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get housing starts data.

        Args:
            region: Region code ("NE", "MW", "S", "W") or None for national
            start_date: Start date for observations
            frequency: Frequency
            limit: Maximum number of observations to return
            sort_order: Sort order ("asc" or "desc")

        Returns:
            List of observations
        """
        if region:
            series_id = f"HOUST{region.upper()}"
        else:
            series_id = self.SERIES["starts_us"]

        return self.get_series_observations(
            series_id=series_id,
            start_date=start_date,
            frequency=frequency,
            limit=limit,
            sort_order=sort_order,
        )

    def get_supply_constraint_indicators(
        self,
        state_code: str,
        years_back: int = 5,
    ) -> Dict[str, Any]:
        """
        Get key supply-constraint indicators for a state.

        Returns building permits, housing starts, and permit trends
        for supply-constraint analysis.

        Args:
            state_code: 2-letter state code
            years_back: How many years of history to fetch

        Returns:
            Dict with permit and starts data
        """
        from datetime import datetime, timedelta

        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=years_back * 365)).strftime(
            "%Y-%m-%d"
        )

        permits = self.get_building_permits(state_code, start_date=start_date)
        starts = self.get_housing_starts(start_date=start_date)

        # Calculate recent trends
        permits_recent = [p for p in permits if p.get("value") != "."]
        starts_recent = [s for s in starts if s.get("value") != "."]

        def calc_growth_rate(observations: List[Dict]) -> Optional[Decimal]:
            """Calculate growth rate from first to last observation."""
            if len(observations) < 2:
                return None
            try:
                first_val = Decimal(observations[0]["value"])
                last_val = Decimal(observations[-1]["value"])
                if first_val == 0:
                    return None
                return (last_val - first_val) / first_val
            except (InvalidOperation, KeyError, ValueError):
                return None

        return {
            "state": state_code,
            "period": f"{start_date} to {end_date}",
            "building_permits": {
                "observations": permits_recent[-12:],  # Last 12 months
                "growth_rate": calc_growth_rate(permits_recent),
                "latest": permits_recent[-1] if permits_recent else None,
            },
            "housing_starts": {
                "observations": starts_recent[-12:],
                "growth_rate": calc_growth_rate(starts_recent),
                "latest": starts_recent[-1] if starts_recent else None,
            },
        }

    def fetch_state_employment_growth(
        self,
        state_code: str,
        years_back: int = 5,
    ) -> Optional[Decimal]:
        """
        Compute 5-year employment growth for a state using FRED nonfarm payroll data.

        Uses the 'All Employees: Total Nonfarm' series (CES survey) to compute
        the change in employment level from the earliest to the latest annual
        average over the specified period.

        Args:
            state_code: 2-letter US state code (e.g., "TX", "CA").
            years_back: Number of years of history to use.

        Returns:
            Decimal growth rate (e.g., 0.0234 = 2.34% growth), or None on error.
        """
        from datetime import datetime, timedelta

        state_code = state_code.strip().upper()
        if not state_code or len(state_code) != 2:
            logger.error(
                "Invalid state code for FRED employment growth: %s", state_code
            )
            return None

        # FRED series ID for state nonfarm payrolls: {STATE}NA
        series_id = f"{state_code}NA"

        end_date = datetime.now()
        start_date = end_date - timedelta(days=years_back * 365)

        try:
            observations = self.get_series_observations(
                series_id,
                start_date=start_date.strftime("%Y-%m-%d"),
                end_date=end_date.strftime("%Y-%m-%d"),
            )
        except FREDAPIError as exc:
            logger.error(
                "FRED employment series %s failed for %s: %s",
                series_id,
                state_code,
                exc,
            )
            return None

        if not observations:
            logger.warning(
                "FRED employment series %s returned no data for %s",
                series_id,
                state_code,
            )
            return None

        # Filter out null values (".") and compute annual averages
        annual_averages: dict[str, list[Decimal]] = {}
        for obs in observations:
            value = obs.get("value")
            date = obs.get("date", "")
            if value is None or value == "." or not date:
                continue
            year = date[:4]
            try:
                decimal_val = Decimal(value)
            except (InvalidOperation, ValueError):
                continue
            if year not in annual_averages:
                annual_averages[year] = []
            annual_averages[year].append(decimal_val)

        # Need at least 2 years of data to compute growth
        years = sorted(annual_averages.keys())
        if len(years) < 2:
            logger.warning(
                "FRED employment series %s needs >=2 years of data, got %d years: %s",
                series_id,
                len(years),
                years,
            )
            return None

        def avg(values: list[Decimal]) -> Decimal:
            return sum(values) / Decimal(len(values))

        earliest_avg = avg(annual_averages[years[0]])
        latest_avg = avg(annual_averages[years[-1]])

        if earliest_avg == 0:
            logger.warning(
                "FRED employment series %s earliest year average is zero for %s",
                series_id,
                state_code,
            )
            return None

        growth_rate = (latest_avg - earliest_avg) / earliest_avg
        logger.info(
            "FRED employment growth for %s (%s): %s → %s = %s%% over %d years",
            state_code,
            series_id,
            f"{earliest_avg:.0f}",
            f"{latest_avg:.0f}",
            f"{float(growth_rate) * 100:.2f}",
            len(years) - 1,
        )
        return growth_rate


def create_fred_adapter() -> FREDAdapter:
    """Factory function to create FRED adapter from environment."""
    return FREDAdapter()

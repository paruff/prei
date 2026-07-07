"""Tests for the Growth Area Explorer view (TASK-4).

Covers:
  - GET renders the state-picker form
  - POST with invalid/missing state shows error
  - POST with missing API keys shows error
  - POST creates and updates GrowthArea rows correctly
  - All places from one state share the same employment_growth_rate
    (state-level BLS data — documented limitation, not a bug)
  - Results sorted by composite_score descending

All HTTP calls are mocked at the import site (core.views) — no real API calls.
"""

from __future__ import annotations

import os
from datetime import timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse
from django.utils import timezone

from core.models import GrowthArea


# ===========================================================================
#  Fixtures / helpers
# ===========================================================================


def _mock_place(
    place_code: str = "44000",
    place_name: str = "Los Angeles",
    population: int = 400000,
) -> dict[str, object]:
    """Build a place dict matching discover_places_in_state output."""
    return {
        "place_code": place_code,
        "place_name": place_name,
        "population": population,
    }


def _mock_census_metrics(
    pop_growth: Decimal = Decimal("0.0526"),
    income_growth: Decimal = Decimal("0.0897"),
) -> dict[str, object]:
    """Build a dict matching fetch_place_growth_metrics output."""
    return {
        "population_current": 400000,
        "population_prior": 380000,
        "population_growth_rate": pop_growth,
        "median_income_current": Decimal("85000"),
        "median_income_prior": Decimal("78000"),
        "median_income_growth_rate": income_growth,
    }


API_ENV = {
    "CENSUS_API_KEY": "test-census-key",
}


# ===========================================================================
#  GET
# ===========================================================================


class TestGrowthExplorerGet:
    """GET behaviour — renders the state-picker form."""

    @pytest.mark.django_db
    def test_get_returns_200(self, client) -> None:
        """GET /growth-explorer/ returns 200 with states in context."""
        resp = client.get(reverse("growth_explorer"))
        assert resp.status_code == 200
        assert "states" in resp.context
        states = resp.context["states"]
        assert len(states) > 0
        assert states[0] == ("AL", "Alabama")

    @pytest.mark.django_db
    def test_get_renders_form_html(self, client) -> None:
        """GET response contains the state-picker form elements."""
        resp = client.get(reverse("growth_explorer"))
        html = resp.content.decode()
        assert "Growth Area Explorer" in html
        assert 'name="state"' in html
        assert "Analyze" in html or "Explore" in html or "Analyze Growth" in html


# ===========================================================================
#  POST — error paths
# ===========================================================================


class TestGrowthExplorerPostErrors:
    """POST behaviour — error handling for invalid input and missing config."""

    @pytest.mark.django_db
    def test_empty_state_shows_error(self, client) -> None:
        """POST with empty state returns form with error message."""
        with patch.dict(os.environ, API_ENV):
            resp = client.post(reverse("growth_explorer"), {"state": ""})

        assert resp.status_code == 200
        assert "Invalid state selected" in resp.content.decode()

    @pytest.mark.django_db
    def test_invalid_state_shows_error(self, client) -> None:
        """POST with invalid state code returns form with error."""
        with patch.dict(os.environ, API_ENV):
            resp = client.post(reverse("growth_explorer"), {"state": "XX"})

        assert resp.status_code == 200
        assert "Invalid state selected" in resp.content.decode()

    @pytest.mark.django_db
    def test_missing_census_key_shows_error(self, client) -> None:
        """POST without CENSUS_API_KEY shows configuration error."""
        with patch.dict(os.environ, clear=True):
            resp = client.post(reverse("growth_explorer"), {"state": "CA"})
            assert resp.status_code == 200
            assert "CENSUS_API_KEY" in resp.content.decode()

    @patch("core.views.discover_places_in_state")
    @pytest.mark.django_db
    def test_no_places_found_shows_error(
        self, mock_discover: MagicMock, client
    ) -> None:
        """POST that finds no places returns error message."""
        mock_discover.return_value = []

        with patch.dict(os.environ, API_ENV):
            resp = client.post(reverse("growth_explorer"), {"state": "WY"})

        assert resp.status_code == 200
        assert "No places found" in resp.content.decode()

    @patch("core.views.discover_places_in_state")
    @pytest.mark.django_db
    def test_place_without_census_data_skipped(
        self, mock_discover: MagicMock, client
    ) -> None:
        """A place that returns None from fetch_place_growth_metrics is skipped
        (not included in results, no GrowthArea created)."""
        mock_discover.return_value = [
            _mock_place("44000", "Good City", 400000),
            _mock_place("55000", "Skip City", 100000),
        ]

        with (
            patch.dict(os.environ, API_ENV),
            patch(
                "core.views.FREDAdapter.fetch_state_employment_growth"
            ) as mock_emp_growth,
            patch("core.views.fetch_place_growth_metrics") as mock_census,
            patch("core.views.fetch_housing_demand_index") as mock_housing,
        ):
            mock_emp_growth.return_value = Decimal("0.0300")
            # First call returns data, second call returns None (fail)
            mock_census.side_effect = [
                _mock_census_metrics(),
                None,
            ]
            mock_housing.return_value = 80

            resp = client.post(reverse("growth_explorer"), {"state": "CA"})

        assert resp.status_code == 200
        # Only the successful place is in the results
        assert GrowthArea.objects.filter(city_name="Good City").exists()
        assert not GrowthArea.objects.filter(city_name="Skip City").exists()
        html = resp.content.decode()
        assert "Good City" in html
        assert "Skip City" not in html


# ===========================================================================
#  POST — success paths
# ===========================================================================


class TestGrowthExplorerPostSuccess:
    """POST behaviour — successful analysis creates/updates GrowthArea rows."""

    @patch("core.views.discover_places_in_state")
    @patch("core.views.FREDAdapter.fetch_state_employment_growth")
    @patch("core.views.fetch_place_growth_metrics")
    @patch("core.views.fetch_housing_demand_index")
    @pytest.mark.django_db
    def test_creates_growth_areas(
        self,
        mock_housing: MagicMock,
        mock_census: MagicMock,
        mock_employment: MagicMock,
        mock_discover: MagicMock,
        client,
    ) -> None:
        """Successful POST creates GrowthArea rows for each place."""
        mock_discover.return_value = [
            _mock_place("44000", "Los Angeles", 400000),
            _mock_place("66000", "San Diego", 100000),
        ]
        mock_employment.return_value = Decimal("0.0450")
        mock_census.return_value = _mock_census_metrics()
        mock_housing.return_value = 85

        with patch.dict(os.environ, API_ENV):
            resp = client.post(reverse("growth_explorer"), {"state": "CA"})

        assert resp.status_code == 200
        assert GrowthArea.objects.filter(state="CA", city_name="Los Angeles").exists()
        assert GrowthArea.objects.filter(state="CA", city_name="San Diego").exists()

        la = GrowthArea.objects.get(state="CA", city_name="Los Angeles")
        # DecimalField(max_digits=6, decimal_places=2) rounds to 2dp
        assert la.employment_growth_rate == Decimal("0.04")  # 0.0450 → 0.04
        assert la.housing_demand_index == 85
        assert la.metro_area == "Los Angeles"

    @patch("core.views.discover_places_in_state")
    @patch("core.views.FREDAdapter.fetch_state_employment_growth")
    @patch("core.views.fetch_place_growth_metrics")
    @patch("core.views.fetch_housing_demand_index")
    @pytest.mark.django_db
    def test_updates_existing_growth_area(
        self,
        mock_housing: MagicMock,
        mock_census: MagicMock,
        mock_employment: MagicMock,
        mock_discover: MagicMock,
        client,
    ) -> None:
        """POST updates an existing GrowthArea with fresh data."""
        GrowthArea.objects.create(
            state="CA",
            city_name="Los Angeles",
            metro_area="Los Angeles",
            population_growth_rate=Decimal("0.0100"),
            employment_growth_rate=Decimal("0.0200"),
            median_income_growth=Decimal("0.0300"),
            housing_demand_index=50,
            data_timestamp=timezone.now() - timedelta(days=30),
        )

        mock_discover.return_value = [_mock_place("44000", "Los Angeles", 410000)]
        mock_employment.return_value = Decimal("0.0550")
        mock_census.return_value = _mock_census_metrics(
            pop_growth=Decimal("0.0789"),
            income_growth=Decimal("0.1538"),
        )
        mock_housing.return_value = 90

        with patch.dict(os.environ, API_ENV):
            resp = client.post(reverse("growth_explorer"), {"state": "CA"})

        assert resp.status_code == 200
        la = GrowthArea.objects.get(state="CA", city_name="Los Angeles")
        # DecimalField(max_digits=6, decimal_places=2) rounds to 2dp
        assert la.population_growth_rate == Decimal("0.08")  # 0.0789 → 0.08
        assert la.employment_growth_rate == Decimal("0.06")  # 0.0550 → 0.06
        assert la.median_income_growth == Decimal("0.15")  # 0.1538 → 0.15
        assert la.housing_demand_index == 90

    @patch("core.views.discover_places_in_state")
    @patch("core.views.FREDAdapter.fetch_state_employment_growth")
    @patch("core.views.fetch_place_growth_metrics")
    @patch("core.views.fetch_housing_demand_index")
    @pytest.mark.django_db
    def test_employment_growth_is_state_level(
        self,
        mock_housing: MagicMock,
        mock_census: MagicMock,
        mock_employment: MagicMock,
        mock_discover: MagicMock,
        client,
    ) -> None:
        """All places from one state share the same employment_growth_rate,
        because the view calls fetch_employment_growth() once and reuses
        the result for every place. This is documented, expected behaviour
        (BLS does not publish place-level employment growth)."""
        mock_discover.return_value = [
            _mock_place("44000", "Los Angeles", 400000),
            _mock_place("66000", "San Diego", 100000),
            _mock_place("70000", "San Jose", 80000),
        ]
        mock_employment.return_value = Decimal("0.0375")  # single state-level value
        mock_census.return_value = _mock_census_metrics()
        mock_housing.return_value = 75

        with patch.dict(os.environ, API_ENV):
            resp = client.post(reverse("growth_explorer"), {"state": "CA"})

        assert resp.status_code == 200
        areas = GrowthArea.objects.filter(state="CA")
        rates = {ga.employment_growth_rate for ga in areas}
        assert len(rates) == 1, (
            f"Expected all places to share the same employment_growth_rate, got {rates}"
        )
        # DecimalField(max_digits=6, decimal_places=2) rounds to 2dp
        assert rates.pop() == Decimal("0.04")  # 0.0375 → 0.04

    @patch("core.views.discover_places_in_state")
    @patch("core.views.FREDAdapter.fetch_state_employment_growth")
    @patch("core.views.fetch_place_growth_metrics")
    @patch("core.views.fetch_housing_demand_index")
    @pytest.mark.django_db
    def test_results_sorted_by_composite_score(
        self,
        mock_housing: MagicMock,
        mock_census: MagicMock,
        mock_employment: MagicMock,
        mock_discover: MagicMock,
        client,
    ) -> None:
        """Results in the response context are sorted by composite_score desc.

        We give each place different data so they produce different scores,
        then verify the render context order."""
        mock_discover.return_value = [
            _mock_place("44000", "Los Angeles", 400000),
            _mock_place("66000", "San Diego", 100000),
            _mock_place("70000", "San Jose", 80000),
        ]
        mock_employment.return_value = Decimal("0.0450")

        # Each place gets different growth data -> different composite_score
        mock_census.side_effect = [
            _mock_census_metrics(
                pop_growth=Decimal("0.1000"), income_growth=Decimal("0.1200")
            ),  # Los Angeles — high
            _mock_census_metrics(
                pop_growth=Decimal("0.0200"), income_growth=Decimal("0.0300")
            ),  # San Diego — low
            _mock_census_metrics(
                pop_growth=Decimal("0.0500"), income_growth=Decimal("0.0600")
            ),  # San Jose — medium
        ]
        mock_housing.side_effect = [90, 60, 75]

        with patch.dict(os.environ, API_ENV):
            resp = client.post(reverse("growth_explorer"), {"state": "CA"})

        assert resp.status_code == 200
        results = resp.context["results"]

        # Verify scores are in descending order
        scores = [r["growth_area"].composite_score for r in results]
        assert scores == sorted(scores, reverse=True), (
            f"Expected composite_scores in descending order, got {scores}"
        )

        # Sanity: Los Angeles (high growth) should rank higher than San Diego (low)
        names_in_order = [r["place_name"] for r in results]
        assert names_in_order.index("Los Angeles") < names_in_order.index(
            "San Diego"
        ), f"Los Angeles should rank above San Diego, got order: {names_in_order}"

    @patch("core.views.discover_places_in_state")
    @patch("core.views.FREDAdapter.fetch_state_employment_growth")
    @patch("core.views.fetch_place_growth_metrics")
    @patch("core.views.fetch_housing_demand_index")
    @pytest.mark.django_db
    def test_context_includes_emp_growth_value(
        self,
        mock_housing: MagicMock,
        mock_census: MagicMock,
        mock_employment: MagicMock,
        mock_discover: MagicMock,
        client,
    ) -> None:
        """The state-level employment growth value is passed to the template
        context so the UI can display it with a footnote."""
        mock_discover.return_value = [_mock_place("44000", "Los Angeles", 400000)]
        mock_employment.return_value = Decimal("0.0375")
        mock_census.return_value = _mock_census_metrics()
        mock_housing.return_value = 80

        with patch.dict(os.environ, API_ENV):
            resp = client.post(reverse("growth_explorer"), {"state": "CA"})

        assert resp.status_code == 200
        assert resp.context["emp_growth"] == Decimal("0.0375")
        assert resp.context["selected_state"] == "CA"

    @patch("core.views.discover_places_in_state")
    @patch("core.views.FREDAdapter.fetch_state_employment_growth")
    @patch("core.views.fetch_place_growth_metrics")
    @patch("core.views.fetch_housing_demand_index")
    @pytest.mark.django_db
    def test_housing_demand_defaults_to_50(
        self,
        mock_housing: MagicMock,
        mock_census: MagicMock,
        mock_employment: MagicMock,
        mock_discover: MagicMock,
        client,
    ) -> None:
        """When fetch_housing_demand_index returns None, the view defaults to 50."""
        mock_discover.return_value = [_mock_place("44000", "Los Angeles", 400000)]
        mock_employment.return_value = Decimal("0.0300")
        mock_census.return_value = _mock_census_metrics()
        mock_housing.return_value = None  # housing API fails

        with patch.dict(os.environ, API_ENV):
            resp = client.post(reverse("growth_explorer"), {"state": "CA"})

        assert resp.status_code == 200
        la = GrowthArea.objects.get(state="CA", city_name="Los Angeles")
        assert la.housing_demand_index == 50, (
            f"Expected default 50 when API returns None, got {la.housing_demand_index}"
        )

"""E2E tests for Rentometer API integration in screening pipeline."""

from unittest.mock import patch

import pytest
from decimal import Decimal

from core.models import PipelineProperty

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture()
def rentometer_property(db, e2e_login, growth_area) -> PipelineProperty:
    """Property without rent data — should trigger Rentometer lookup."""
    return PipelineProperty.objects.create(
        user=e2e_login,
        source_type=PipelineProperty.SourceType.HUD,
        source_id="RENT-001",
        address="456 Oak Ave",
        city="Austin",
        state="TX",
        zip_code="78704",
        county="Travis",
        growth_area=growth_area,
        stage=PipelineProperty.Stage.SCREENING,
        status=PipelineProperty.Status.ACTIVE,
        screening_passed=None,
        price=Decimal("180000"),
        beds=3,
    )


class TestRentometerE2E:
    def test_extract_zip_from_property(self, rentometer_property) -> None:
        """_extract_zip correctly extracts ZIP from PipelineProperty."""
        from core.services.screening import _extract_zip

        zip_code = _extract_zip(None, rentometer_property)
        assert zip_code == "78704"

    def test_extract_zip_from_address(self, rentometer_property) -> None:
        """_extract_zip extracts ZIP from address when zip_code is empty."""
        rentometer_property.zip_code = ""
        rentometer_property.address = "123 Main St, Austin, TX 78701"
        from core.services.screening import _extract_zip

        zip_code = _extract_zip(None, rentometer_property)
        assert zip_code == "78701"

    def test_rentometer_returns_none_without_api_key(self, rentometer_property) -> None:
        """get_rent_estimate returns None when no API key configured."""
        from core.integrations.market.rentometer import get_rent_estimate

        with self._override_settings(RENTO_METER_API_KEY=""):
            result = get_rent_estimate(
                zip_code="78704",
                address="456 Oak Ave",
                city="Austin",
                state="TX",
            )
            assert result is None

    def test_screening_uses_estimated_rent(self, rentometer_property) -> None:
        """Screening uses estimated_rent when set on property."""
        rentometer_property.estimated_rent = Decimal("2100.00")
        rentometer_property.save(update_fields=["estimated_rent"])

        from core.services.screening import _get_monthly_rent

        rent = _get_monthly_rent(rentometer_property, None)
        assert rent == Decimal("2100.00")

    def test_screening_falls_back_to_hud_fmr(self, rentometer_property) -> None:
        """Screening falls back to HUD FMR when no rent data available."""
        from core.services.screening import _get_monthly_rent

        # With no API key, should return None (no FMR fallback in test env)
        rent = _get_monthly_rent(rentometer_property, None)
        # In test env without HUD API key, this returns None
        assert rent is None

    def test_extract_zip_prefers_trailing_zip_over_house_number(
        self, rentometer_property
    ) -> None:
        """A 5-digit house number earlier in the address must not be mistaken
        for the ZIP when the real ZIP trails the address."""
        rentometer_property.zip_code = ""
        rentometer_property.address = "12345 Main St, Austin, TX 78701"
        from core.services.screening import _extract_zip

        zip_code = _extract_zip(None, rentometer_property)
        assert zip_code == "78701"

    def test_get_monthly_rent_uses_rentometer_when_available(
        self, rentometer_property
    ) -> None:
        """_get_monthly_rent uses and persists a Rentometer estimate when found."""
        from core.services.screening import _get_monthly_rent

        with patch(
            "core.integrations.market.rentometer.get_rent_estimate",
            return_value=Decimal("1950.00"),
        ):
            rent = _get_monthly_rent(rentometer_property, None)

        assert rent == Decimal("1950.00")
        rentometer_property.refresh_from_db()
        assert rentometer_property.estimated_rent == Decimal("1950.00")

    def test_get_monthly_rent_falls_back_to_hud_fmr_when_rentometer_fails(
        self, rentometer_property
    ) -> None:
        """When Rentometer finds nothing, the chain falls through to HUD FMR."""
        from core.services.screening import _get_monthly_rent

        with (
            patch(
                "core.integrations.market.rentometer.get_rent_estimate",
                return_value=None,
            ),
            patch(
                "core.integrations.market.hud_fmr.get_rent_estimate",
                return_value=Decimal("1500.00"),
            ),
        ):
            rent = _get_monthly_rent(rentometer_property, None)

        assert rent == Decimal("1500.00")
        rentometer_property.refresh_from_db()
        assert rentometer_property.estimated_rent == Decimal("1500.00")

    def test_get_monthly_rent_cache_rent_false_skips_db_write(
        self, rentometer_property
    ) -> None:
        """cache_rent=False (screening_preview) returns the rent but never saves it."""
        from core.services.screening import _get_monthly_rent

        with patch(
            "core.integrations.market.rentometer.get_rent_estimate",
            return_value=Decimal("1950.00"),
        ):
            rent = _get_monthly_rent(rentometer_property, None, cache_rent=False)

        assert rent == Decimal("1950.00")
        rentometer_property.refresh_from_db()
        assert rentometer_property.estimated_rent is None

    def test_get_monthly_rent_never_crashes_for_hud_usda_pipeline_view(
        self, growth_area
    ) -> None:
        """A raw HudProperty (adapted to _PipelineView, no pk) must not crash
        _get_monthly_rent even when a rent value is found."""
        from core.models.sources import HudProperty
        from core.services.screening import _adapt_source_to_pipeline

        hud_property = HudProperty(
            address="456 Oak Ave",
            city="Austin",
            state="TX",
            zip_code="78704",
        )
        view = _adapt_source_to_pipeline(hud_property)
        assert view.address == "456 Oak Ave"
        assert view.city == "Austin"
        assert view.state == "TX"

        from core.services.screening import _get_monthly_rent

        with patch(
            "core.integrations.market.rentometer.get_rent_estimate",
            return_value=Decimal("1700.00"),
        ):
            rent = _get_monthly_rent(view, hud_property)

        assert rent == Decimal("1700.00")

    @staticmethod
    def _override_settings(**kwargs):
        """Context manager to override Django settings."""
        from django.test import override_settings

        return override_settings(**kwargs)

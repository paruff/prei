"""E2E tests for the full pipeline (discovery → screening → underwriting → offer).

The prei orchestrator class was deleted in the pydantic→Django
consolidation; these tests compose the new core services explicitly.
"""

import pytest
from decimal import Decimal

from core.services.discovery_processor import process_discovery_batch
from core.services.screening import ScreeningThresholds, screen_batch
from core.services.underwriting import (
    UnderwritingInput,
    UnderwritingMetrics,
    solve_underwriting,
)
from core.services.offer import OfferInput, OfferStrategy, solve_offer

PROPERTIES = [
    {
        "id": "E2E-FP-1",
        "address": "100 Prime St",
        "price": 300000,
        "rent": 2800,
        "beds": 3,
        "baths": 2,
    },
    {
        "id": "E2E-FP-2",
        "address": "200 Value Ave",
        "price": 220000,
        "rent": 2000,
        "beds": 3,
        "baths": 1,
    },
]

FAILING = {
    "id": "E2E-FAIL",
    "address": "999 Bad Rd",
    "price": 600000,
    "rent": 1500,
    "beds": 1,
    "baths": 0.5,
}

THRESHOLDS = ScreeningThresholds(
    min_gross_yield=0.07, max_price_to_rent_ratio=15.0, min_beds=2, min_baths=1
)


def _to_screening_dict(p: dict) -> dict:
    return {
        "asset_id": p["id"],
        "address": p["address"],
        "estimated_monthly_rent": p["rent"],
        "purchase_price": p["price"],
        "beds": p["beds"],
        "baths": p["baths"],
    }


def _underwrite(p: dict) -> UnderwritingMetrics:
    return solve_underwriting(
        UnderwritingInput(
            purchase_price=Decimal(str(p["price"])),
            estimated_rent=Decimal(str(p["rent"])),
            property_tax_annual=Decimal("3600"),
            insurance_annual=Decimal("1200"),
        ),
        target_cap_rate=0.08,
    )


@pytest.mark.e2e
class TestPipelineE2E:
    def test_full_pipeline_happy_path(self):
        """All properties pass screening and produce underwriting metrics."""
        result = process_discovery_batch(PROPERTIES, source_name="e2e")
        assert result["new_assets_discovered"] == 2
        assert result["failed_records"] == 0

        summary = screen_batch([_to_screening_dict(p) for p in PROPERTIES], THRESHOLDS)
        assert summary["advanced"] == 2
        assert summary["killed"] == 0

        for p in PROPERTIES:
            uw = _underwrite(p)
            assert uw.noi > 0
            assert uw.mao > 0

    def test_pipeline_rejects_failing_property(self):
        """Property failing screening is killed."""
        summary = screen_batch([_to_screening_dict(FAILING)], THRESHOLDS)
        assert summary["killed"] == 1
        assert summary["advanced"] == 0

    def test_pipeline_dedup(self):
        """Same address run twice → second is duplicate."""
        existing: set[str] = set()
        r1 = process_discovery_batch(
            PROPERTIES[:1], source_name="e2e", existing_hashes=existing
        )
        assert r1["new_assets_discovered"] == 1
        r2 = process_discovery_batch(
            PROPERTIES[:1], source_name="e2e", existing_hashes=existing
        )
        assert r2["new_assets_discovered"] == 0
        assert r2["duplicates_skipped"] == 1

    def test_pipeline_with_offer(self):
        """Pipeline → underwriting → offer chain works."""
        uw = _underwrite(PROPERTIES[0])
        offer = solve_offer(OfferInput(mao=uw.mao), OfferStrategy.TARGET)
        assert offer.offer_price > 0
        assert offer.premium_pct == pytest.approx(0, abs=Decimal("0.0001"))

    def test_multi_property_pipeline(self):
        """Multiple properties processed sequentially produce distinct caps."""
        cap_rates = [_underwrite(p).cap_rate for p in PROPERTIES]
        assert cap_rates[0] != cap_rates[1]

"""Integration and E2E tests for the screening stage."""

import pytest

from core.services.screening import (
    ScreeningThresholds,
    evaluate_screening_stage,
    gross_yield,
    price_to_rent_ratio,
    compute_screening_metrics,
    screen_batch,
)

# ═══════════════════════════════════════════════════════════════════════════════
#  INTEGRATION — screening math + batch
# ═══════════════════════════════════════════════════════════════════════════════

THRESHOLDS = ScreeningThresholds(
    min_gross_yield=0.07, max_price_to_rent_ratio=15.0, min_beds=2, min_baths=1
)


class TestScreeningIntegration:
    def test_gross_yield_vs_price_to_rent_consistency(self):
        """gross_yield and price_to_rent_ratio are mathematical inverses."""
        gy = gross_yield(2500, 300000)
        ptr = price_to_rent_ratio(2500, 300000)
        assert gy == pytest.approx(1 / ptr, rel=1e-6)

    @pytest.mark.parametrize(
        "rent,price,expected_yield,expected_ptr",
        [
            (2000, 300000, 0.08, 12.5),
            (1500, 250000, 0.072, 13.889),
            (3000, 500000, 0.072, 13.889),
        ],
    )
    def test_compute_screening_metrics_consistency(
        self, rent, price, expected_yield, expected_ptr
    ):
        metrics = compute_screening_metrics(
            {"estimated_monthly_rent": rent, "purchase_price": price}
        )
        assert metrics["gross_yield"] == pytest.approx(expected_yield, rel=1e-3)
        assert metrics["price_to_rent_ratio"] == pytest.approx(expected_ptr, rel=1e-3)

    def test_screen_batch_with_custom_thresholds(self):
        """screen_batch with relaxed thresholds passes all."""
        relaxed = ScreeningThresholds(
            min_gross_yield=0.03, max_price_to_rent_ratio=30.0, min_beds=1, min_baths=1
        )
        payloads = [
            {
                "asset_id": "A",
                "address": "1 St",
                "estimated_monthly_rent": 1500,
                "purchase_price": 500000,
                "beds": 1,
                "baths": 1,
            },  # 3.6% > 3% ✓
            {
                "asset_id": "B",
                "address": "2 St",
                "estimated_monthly_rent": 2000,
                "purchase_price": 400000,
                "beds": 2,
                "baths": 1,
            },
        ]
        result = screen_batch(payloads, relaxed)
        assert result["advanced"] == 2


# ═══════════════════════════════════════════════════════════════════════════════
#  E2E — screening as part of full pipeline
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.e2e
class TestScreeningE2E:
    def test_e2e_screening_passing_and_failing(self):
        """evaluate_screening_stage distinguishes passing and failing properties."""
        passing = {
            "id": "P",
            "address": "100 Good St",
            "estimated_monthly_rent": 2000,
            "purchase_price": 200000,
            "beds": 3,
            "baths": 2,
        }
        failing = {
            "id": "F",
            "address": "200 Bad St",
            "estimated_monthly_rent": 1000,
            "purchase_price": 500000,
            "beds": 1,
            "baths": 0.5,
        }
        assert evaluate_screening_stage(passing, THRESHOLDS)[0] is True
        assert evaluate_screening_stage(failing, THRESHOLDS)[0] is False

    def test_e2e_discover_then_screen(self):
        """Discover → screen in sequence (orchestrator equivalent)."""
        from core.services.discovery_processor import process_discovery_batch

        existing: set[str] = set()
        batch = [
            {
                "id": "E2E-1",
                "address": "10 Main",
                "price": 300000,
                "rent": 2500,
                "beds": 3,
                "baths": 2,
            },
            {
                "id": "E2E-2",
                "address": "20 Oak",
                "price": 200000,
                "rent": 1800,
                "beds": 2,
                "baths": 1,
            },
        ]
        discovered = process_discovery_batch(
            batch, source_name="e2e", existing_hashes=existing
        )
        assert discovered["new_assets_discovered"] == 2

        screening_payloads = [
            {
                "asset_id": p["id"],
                "address": p["address"],
                "estimated_monthly_rent": p["rent"],
                "purchase_price": p["price"],
                "beds": p["beds"],
                "baths": p["baths"],
            }
            for p in batch
        ]
        summary = screen_batch(screening_payloads, THRESHOLDS)
        assert summary["advanced"] == 2
        assert summary["killed"] == 0

"""Pipeline orchestrator — chains discovery → screening → underwriting.

Runs a single property payload through the full pipeline pipeline,
returning the final asset state and all computed metrics.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Set

from prei.models.pipeline import PipelineStage, PropertyAsset
from prei.pipeline.engine import (
    AssetRepository,
    InMemoryAssetRepository,
    PipelineEngine,
)
from prei.pipeline.handlers.discovery import DiscoverySanitizer
from prei.pipeline.handlers.screening import (
    ScreeningThresholds,
    evaluate_screening_stage,
)
from prei.pipeline.handlers.underwriting import (
    UnderwritingInput,
    UnderwritingMetrics,
    solve_underwriting,
)

logger = logging.getLogger(__name__)


# ── Config ────────────────────────────────────────────────────────────────────

DEFAULT_SCREENING_THRESHOLDS = ScreeningThresholds(
    min_gross_yield=0.07,
    max_price_to_rent_ratio=15.0,
    min_beds=1,
    min_baths=1,
)

DEFAULT_TARGET_CAP_RATE = 0.08


# ── Result model ──────────────────────────────────────────────────────────────


class PipelineResult:
    """Container for the full pipeline execution result."""

    def __init__(
        self,
        asset: Optional[PropertyAsset] = None,
        canonical: Optional[Any] = None,
        screening_passed: Optional[bool] = None,
        screening_reason: Optional[str] = None,
        underwriting: Optional[UnderwritingMetrics] = None,
        error: Optional[str] = None,
    ) -> None:
        self.asset = asset
        self.canonical = canonical
        self.screening_passed = screening_passed
        self.screening_reason = screening_reason
        self.underwriting = underwriting
        self.error = error

    @property
    def success(self) -> bool:
        """True if the pipeline completed without error."""
        return self.error is None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a JSON-safe dict."""
        base: Dict[str, Any] = {
            "success": self.success,
        }
        if self.error:
            base["error"] = self.error
            return base

        base["asset_id"] = self.asset.asset_id if self.asset else None
        base["current_stage"] = self.asset.current_stage.value if self.asset else None

        if self.canonical:
            base["address_hash"] = self.canonical.address_hash
            base["price"] = self.canonical.price
            base["beds"] = self.canonical.beds
            base["baths"] = self.canonical.baths

        base["screening_passed"] = self.screening_passed

        if self.underwriting:
            base["noi"] = self.underwriting.noi
            base["cap_rate"] = self.underwriting.cap_rate
            base["cash_on_cash"] = self.underwriting.cash_on_cash
            base["mao"] = self.underwriting.mao
            base["target_cap_rate"] = DEFAULT_TARGET_CAP_RATE

        return base


# ── Orchestrator ──────────────────────────────────────────────────────────────


class PipelineOrchestrator:
    """Orchestrates a full pipeline run for a single property.

    Stages executed in order:
      1. DISCOVERY  — normalize raw data via DiscoverySanitizer
      2. SCREENING  — evaluate against thresholds
      3. UNDERWRITING — compute NOI, cap rate, CoC, MAO

    The asset advances through pipeline stages via the PipelineEngine
    so hooks and persistence are respected at each transition.
    """

    def __init__(
        self,
        repository: Optional[AssetRepository] = None,
        screening_thresholds: Optional[ScreeningThresholds] = None,
        target_cap_rate: float = DEFAULT_TARGET_CAP_RATE,
        existing_hashes: Optional[Set[str]] = None,
    ) -> None:
        self.repository = repository or InMemoryAssetRepository()
        self.engine = PipelineEngine(repository=self.repository)
        self.screening_thresholds = screening_thresholds or DEFAULT_SCREENING_THRESHOLDS
        self.target_cap_rate = target_cap_rate
        self.existing_hashes = existing_hashes or set()

    # ── Public entry point ───────────────────────────────────────────────────

    def run(
        self,
        raw_payload: Dict[str, Any],
        source_name: str = "pipeline_orchestrator",
    ) -> PipelineResult:
        """Execute the full pipeline on a single raw property payload.

        Args:
            raw_payload: Raw property data dict (any source schema).
            source_name: Source label for the discovery stage.

        Returns:
            PipelineResult with asset state and all computed metrics.
        """
        # ── Stage 1: DISCOVERY ───────────────────────────────────────────
        try:
            canonical = DiscoverySanitizer.transform_input(raw_payload, source_name)
        except ValueError as exc:
            return PipelineResult(error=f"Discovery failed: {exc}")

        # Dedup check
        if canonical.address_hash in self.existing_hashes:
            return PipelineResult(
                error=f"Duplicate address hash: {canonical.address_hash}"
            )
        self.existing_hashes.add(canonical.address_hash)

        # ── Stage 2: SCREENING ───────────────────────────────────────────
        asset_data = {
            "estimated_monthly_rent": canonical.estimated_rent,
            "purchase_price": canonical.price,
            "beds": canonical.beds,
            "baths": canonical.baths,
        }
        screening_passed, screening_reason = evaluate_screening_stage(
            asset_data, self.screening_thresholds
        )

        if not screening_passed:
            # Create asset and kill it with the violation reason
            asset = PropertyAsset(
                asset_id=canonical.source_id,
                address=canonical.raw_address,
            )
            self.repository.save(asset)
            asset = self.engine.process_transition(
                asset,
                PipelineStage.KILLED,
                {
                    "reason": screening_reason,
                    "violation_reason": screening_reason,
                    "source": source_name,
                    "address_hash": canonical.address_hash,
                },
            )
            return PipelineResult(
                asset=asset,
                canonical=canonical,
                screening_passed=False,
                screening_reason=screening_reason,
            )

        # ── Stage 3: UNDERWRITING ────────────────────────────────────────
        # Build input from canonical data (with sensible defaults)
        price = canonical.price or 0.0
        rent = canonical.estimated_rent or 0.0
        uw_input = UnderwritingInput(
            purchase_price=price,
            estimated_rent=rent,
            property_tax_annual=raw_payload.get("property_tax_annual", price * 0.012),
            insurance_annual=raw_payload.get("insurance_annual", price * 0.004),
            hoa_annual=raw_payload.get("hoa_annual", 0.0),
        )
        uw_metrics = solve_underwriting(uw_input, self.target_cap_rate)

        # ── Create asset and advance through pipeline stages ─────────────
        asset = PropertyAsset(
            asset_id=canonical.source_id,
            address=canonical.raw_address,
        )
        self.repository.save(asset)

        ctx = {
            "source": source_name,
            "address_hash": canonical.address_hash,
            "price": canonical.price,
            "estimated_rent": canonical.estimated_rent,
            "underwriting": uw_metrics.model_dump(),
        }

        # GACS → DISCOVERY
        asset = self.engine.process_transition(
            asset, PipelineStage.DISCOVERY, {**ctx, "reason": "Discovery completed"}
        )
        # DISCOVERY → SCREENING
        asset = self.engine.process_transition(
            asset, PipelineStage.SCREENING, {**ctx, "reason": "Screening passed"}
        )
        # SCREENING → UNDERWRITING
        asset = self.engine.process_transition(
            asset,
            PipelineStage.UNDERWRITING,
            {**ctx, "reason": "Underwriting completed"},
        )

        return PipelineResult(
            asset=asset,
            canonical=canonical,
            screening_passed=True,
            underwriting=uw_metrics,
        )

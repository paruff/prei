"""Vectorized parallel screening pipeline for high-throughput batch processing.

Wraps the single-property screening evaluator in a multi-threaded worker
to clear massive discovery queues efficiently — thousands of properties
per batch with sub-second total execution.
"""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List

from prei.models.pipeline import PipelineStage, PropertyAsset
from prei.pipeline.engine import PipelineEngine
from prei.pipeline.handlers.screening import (
    ScreeningThresholds,
    evaluate_screening_stage,
)

logger = logging.getLogger(__name__)


class BatchScreeningProcessor:
    """Evaluate a batch of property payloads through the SCREENING stage.

    Each property is independently evaluated against the configured
    thresholds using the hyper-fast screening evaluator. Passing
    properties advance to UNDERWRITING; failing properties are
    killed with the exact violation reason recorded.

    Args:
        engine: PipelineEngine instance for asset persistence and hooks.
        thresholds: ScreeningThresholds for the evaluator.
        max_workers: Number of parallel worker threads (default 8).
    """

    def __init__(
        self,
        engine: PipelineEngine,
        thresholds: ScreeningThresholds,
        max_workers: int = 8,
    ) -> None:
        self.engine = engine
        self.thresholds = thresholds
        self.max_workers = max_workers

    # ── Public API ────────────────────────────────────────────────────────────

    def process(
        self,
        property_dicts: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Evaluate a batch of property payloads through SCREENING.

        Each payload is a dict with at minimum:
            asset_id (str): Unique identifier.
            address (str): Property address.
            estimated_monthly_rent (float): Projected rent.
            purchase_price (float): Acquisition price.
            beds (int): Bedroom count.
            baths (int | float): Bathroom count.
            hoa_name (str, optional): HOA name for exclusion check.

        Args:
            property_dicts: List of property payload dicts.

        Returns:
            Operational summary dict:
                processed (int): Total payloads in the batch.
                advanced (int): Payloads that passed → UNDERWRITING.
                killed (int): Payloads that failed → KILLED.
                execution_time_ms (float): Wall-clock time in ms.
        """
        start = time.perf_counter()
        advanced = 0
        killed = 0
        errors: List[str] = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures = {
                pool.submit(self._process_single, payload): payload
                for payload in property_dicts
            }
            for future in as_completed(futures):
                payload = futures[future]
                try:
                    result = future.result()
                    if result is True:
                        advanced += 1
                    else:
                        killed += 1
                except Exception as exc:
                    logger.error(
                        "Batch screening failed for asset %s: %s",
                        payload.get("asset_id", "?"),
                        exc,
                    )
                    errors.append(f"{payload.get('asset_id', '?')}: {exc}")
                    killed += 1

        elapsed_ms = (time.perf_counter() - start) * 1000

        summary: Dict[str, Any] = {
            "processed": len(property_dicts),
            "advanced": advanced,
            "killed": killed,
            "execution_time_ms": round(elapsed_ms, 2),
        }
        if errors:
            summary["errors"] = errors

        logger.info(
            "Batch screening complete: %d processed, %d advanced, %d killed in %.1fms",
            summary["processed"],
            summary["advanced"],
            summary["killed"],
            summary["execution_time_ms"],
        )
        return summary

    # ── Internal per-asset logic ──────────────────────────────────────────────

    def _process_single(
        self,
        payload: Dict[str, Any],
    ) -> bool:
        """Evaluate one property payload and advance or kill its asset.

        Returns True if the asset advanced to UNDERWRITING,
        False if it was killed.
        """
        asset_id = payload.get("asset_id", "unknown")
        address = payload.get("address", "")

        # Build asset_data dict for the screening evaluator
        asset_data = _extract_screening_data(payload)

        # Run the screener
        passed, fail_reason = evaluate_screening_stage(asset_data, self.thresholds)

        # Build transition context with screening metrics
        ctx: Dict[str, Any] = {
            "source": "batch_screening",
            "asset_data": asset_data,
        }

        # Load or create the PropertyAsset for engine tracking
        asset = self.engine.repository.load(asset_id)
        if asset is None:
            asset = PropertyAsset(asset_id=asset_id, address=address)
            self.engine.repository.save(asset)

        # Advance from GACS → DISCOVERY → SCREENING if needed
        if asset.current_stage == PipelineStage.GACS:
            ctx["reason"] = "Auto-advance through discovery"
            asset = self.engine.process_transition(
                asset,
                PipelineStage.DISCOVERY,
                {"reason": "Batch screening auto-advance"},
            )
            asset = self.engine.process_transition(
                asset,
                PipelineStage.SCREENING,
                {"reason": "Batch screening auto-advance"},
            )

        # Now evaluate and transition from SCREENING
        if passed:
            ctx["reason"] = "Screening passed"
            self.engine.process_transition(asset, PipelineStage.UNDERWRITING, ctx)
            return True
        else:
            ctx["violation_reason"] = fail_reason or "Screening failed"
            ctx["reason"] = ctx["violation_reason"]
            self.engine.process_transition(asset, PipelineStage.KILLED, ctx)
            return False


# ── Helper ────────────────────────────────────────────────────────────────────


def _extract_screening_data(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Extract the fields the screening evaluator needs from a raw payload.

    Unknown or missing fields pass through as None so the evaluator
    can skip missing checks gracefully.
    """
    return {
        "estimated_monthly_rent": payload.get("estimated_monthly_rent"),
        "purchase_price": payload.get("purchase_price"),
        "beds": payload.get("beds"),
        "baths": payload.get("baths"),
        "hoa_name": payload.get("hoa_name"),
    }

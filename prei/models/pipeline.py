"""Pipeline state machine for property asset lifecycle.

Defines the immutable stage hierarchy, historical stage log structures,
and an explicit transition state manager using pydantic v2 and Python enums.

Pipeline stages (11 values):
  GACS → DISCOVERY → SCREENING → UNDERWRITING → OFFER → DUE_DILIGENCE →
  CLOSING → TURNOVER → LEASING ↔ PORTFOLIO

Any stage can transition to KILLED (terminal). No asset can exit KILLED.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PipelineStage(str, Enum):
    """Exact 11-stage pipeline lifecycle for a property asset."""

    GACS = "GACS"
    DISCOVERY = "DISCOVERY"
    SCREENING = "SCREENING"
    UNDERWRITING = "UNDERWRITING"
    OFFER = "OFFER"
    DUE_DILIGENCE = "DUE_DILIGENCE"
    CLOSING = "CLOSING"
    TURNOVER = "TURNOVER"
    LEASING = "LEASING"
    PORTFOLIO = "PORTFOLIO"
    KILLED = "KILLED"


class InvalidStageTransitionException(Exception):
    """Raised when an illegal stage transition is attempted."""

    pass


class StageLog(BaseModel):
    """Immutable record of a single stage occupancy period."""

    stage: PipelineStage
    entered_at: datetime = Field(default_factory=datetime.utcnow)
    exited_at: Optional[datetime] = None
    reason: Optional[str] = None
    metrics_snapshot: Dict[str, Any] = Field(default_factory=dict)


class PropertyAsset(BaseModel):
    """A property asset tracked through the pipeline state machine.

    Attributes:
        asset_id: Unique identifier for the asset.
        address: Property street address.
        current_stage: The asset's current pipeline stage.
        stage_history: Ordered list of StageLog entries (most recent last).
        kill_reason: Populated only when current_stage == KILLED.
    """

    asset_id: str
    address: str
    current_stage: PipelineStage = PipelineStage.GACS
    stage_history: List[StageLog] = Field(default_factory=list)
    kill_reason: Optional[str] = None

    # ── Static transition ruleset ──────────────────────────────────────────
    # Maps each stage to its allowed next stages.
    # KILLED is explicitly included where allowed and is terminal (no outgoing).
    ALLOWED_TRANSITIONS: Dict[PipelineStage, List[PipelineStage]] = {
        PipelineStage.GACS: [PipelineStage.DISCOVERY, PipelineStage.KILLED],
        PipelineStage.DISCOVERY: [PipelineStage.SCREENING, PipelineStage.KILLED],
        PipelineStage.SCREENING: [PipelineStage.UNDERWRITING, PipelineStage.KILLED],
        PipelineStage.UNDERWRITING: [PipelineStage.OFFER, PipelineStage.KILLED],
        PipelineStage.OFFER: [PipelineStage.DUE_DILIGENCE, PipelineStage.KILLED],
        PipelineStage.DUE_DILIGENCE: [PipelineStage.CLOSING, PipelineStage.KILLED],
        PipelineStage.CLOSING: [PipelineStage.TURNOVER, PipelineStage.KILLED],
        PipelineStage.TURNOVER: [PipelineStage.LEASING, PipelineStage.KILLED],
        PipelineStage.LEASING: [PipelineStage.PORTFOLIO, PipelineStage.KILLED],
        PipelineStage.PORTFOLIO: [PipelineStage.LEASING, PipelineStage.KILLED],
        PipelineStage.KILLED: [],  # terminal — no transitions out
    }

    def transition_to(
        self,
        next_stage: PipelineStage,
        reason: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Attempt a deterministic stage transition.

        Args:
            next_stage: Target pipeline stage.
            reason: Optional human-readable explanation for the transition.
            metrics: Optional snapshot of key metrics at transition time.

        Raises:
            InvalidStageTransitionException: If the transition is not allowed
                by the static ruleset.
        """
        if next_stage not in self.ALLOWED_TRANSITIONS[self.current_stage]:
            raise InvalidStageTransitionException(
                f"Illegal transition from {self.current_stage.value} "
                f"to {next_stage.value}"
            )

        now = datetime.utcnow()

        # Close the previous stage's exit timestamp
        if self.stage_history:
            self.stage_history[-1].exited_at = now

        # Append the new stage log entry
        self.stage_history.append(
            StageLog(
                stage=next_stage,
                entered_at=now,
                reason=reason,
                metrics_snapshot=metrics or {},
            )
        )
        self.current_stage = next_stage

        # Persist kill_reason when transitioning to terminal state
        if next_stage == PipelineStage.KILLED:
            self.kill_reason = reason

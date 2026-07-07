"""REST API endpoints for the property pipeline engine.

Exposes pipeline summary statistics and manual transition controls
via FastAPI. Designed to run as a standalone microservice decoupled
from the Django application layer.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException

from prei.models.pipeline import (
    InvalidStageTransitionException,
    PipelineStage,
    PropertyAsset,
)
from prei.pipeline.engine import (
    AssetRepository,
    InMemoryAssetRepository,
    PipelineEngine,
    StateAggregator,
)

router = APIRouter(prefix="/api/v1/pipeline", tags=["pipeline"])


# ── Dependency injection ──────────────────────────────────────────────────────
# In production, replace with a properly configured SqliteAssetRepository
# or Django-model-backed repository.

_repository: Optional[AssetRepository] = None
_engine: Optional[PipelineEngine] = None


def get_repository() -> AssetRepository:
    """Return the shared repository instance."""
    global _repository
    if _repository is None:
        _repository = InMemoryAssetRepository()
    return _repository


def get_engine() -> PipelineEngine:
    """Return the shared pipeline engine instance."""
    global _engine
    if _engine is None:
        _engine = PipelineEngine(repository=get_repository())
    return _engine


def configure_repository(repo: AssetRepository) -> None:
    """Override the default repository (used by tests)."""
    global _repository, _engine
    _repository = repo
    _engine = PipelineEngine(repository=repo)


# ── Helper ────────────────────────────────────────────────────────────────────


def _asset_to_dict(asset: PropertyAsset) -> Dict[str, Any]:
    """Serialize a PropertyAsset to a JSON-safe dict."""
    return {
        "asset_id": asset.asset_id,
        "address": asset.address,
        "current_stage": asset.current_stage.value,
        "stage_history": [
            {
                "stage": log.stage.value,
                "entered_at": log.entered_at.isoformat() if log.entered_at else None,
                "exited_at": log.exited_at.isoformat() if log.exited_at else None,
                "reason": log.reason,
            }
            for log in asset.stage_history
        ],
        "kill_reason": asset.kill_reason,
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  Endpoints
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/summary")
def get_pipeline_summary() -> Dict[str, Any]:
    """Return aggregate pipeline statistics.

    Returns asset counts grouped by pipeline stage plus a high-level
    pipeline_flow breakdown and total/killed counts.
    """
    repo = get_repository()
    aggregator = StateAggregator(repo)
    return aggregator.summary()


@router.get("/assets")
def list_assets() -> List[Dict[str, Any]]:
    """Return all assets with their current stage and history."""
    repo = get_repository()
    return [_asset_to_dict(a) for a in repo.list_all()]


@router.get("/assets/{asset_id}")
def get_asset(asset_id: str) -> Dict[str, Any]:
    """Return a single asset by ID."""
    repo = get_repository()
    asset = repo.load(asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail=f"Asset {asset_id} not found")
    return _asset_to_dict(asset)


@router.post("/assets")
def create_asset(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new asset at GACS stage.

    Request body:
        asset_id (str, required): Unique identifier.
        address (str, required): Property address.
    """
    asset_id = payload.get("asset_id")
    address = payload.get("address")
    if not asset_id or not address:
        raise HTTPException(
            status_code=422,
            detail="Both 'asset_id' and 'address' are required",
        )
    repo = get_repository()
    existing = repo.load(asset_id)
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Asset {asset_id} already exists",
        )
    asset = PropertyAsset(asset_id=asset_id, address=address)
    repo.save(asset)
    return _asset_to_dict(asset)


@router.post("/transition")
def force_transition(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Force a manual state transition for an asset.

    Request body:
        asset_id (str, required): The asset to transition.
        target_stage (str, required): Target pipeline stage name.
        reason (str, optional): Human-readable explanation.
        context (dict, optional): Additional metrics context.

    Returns the updated asset state.

    Raises 422 if the transition violates the state machine ruleset.
    """
    asset_id = payload.get("asset_id")
    target = payload.get("target_stage")
    reason = payload.get("reason")
    context = payload.get("context", {})

    if not asset_id or not target:
        raise HTTPException(
            status_code=422,
            detail="Both 'asset_id' and 'target_stage' are required",
        )

    repo = get_repository()
    asset = repo.load(asset_id)
    if asset is None:
        raise HTTPException(
            status_code=404,
            detail=f"Asset {asset_id} not found",
        )

    try:
        target_stage = PipelineStage(target)
    except ValueError:
        valid = [s.value for s in PipelineStage]
        raise HTTPException(
            status_code=422,
            detail=f"Invalid stage '{target}'. Valid values: {valid}",
        )

    ctx: Dict[str, Any] = {**context}
    if reason:
        ctx["reason"] = reason

    engine = get_engine()
    try:
        updated = engine.process_transition(asset, target_stage, ctx)
    except InvalidStageTransitionException as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return _asset_to_dict(updated)


@router.delete("/assets/{asset_id}")
def delete_asset(asset_id: str) -> Dict[str, str]:
    """Remove an asset from the repository entirely."""
    # Note: InMemoryAssetRepository doesn't support delete.
    # For now, we transition the asset to KILLED as a soft delete.
    repo = get_repository()
    asset = repo.load(asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail=f"Asset {asset_id} not found")
    engine = get_engine()
    engine.process_transition(asset, PipelineStage.KILLED, {"reason": "API delete"})
    return {"status": "killed", "asset_id": asset_id}

"""Pipeline engine for batch-processing assets through stage transitions.

Provides the PipelineEngine class with hook-based pre-transition evaluation,
a repository abstraction for asset persistence, and an in-memory repository
implementation for testing.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, cast

from prei.models.pipeline import (
    PipelineStage,
    PropertyAsset,
)

logger = logging.getLogger(__name__)

# ── Type aliases ──────────────────────────────────────────────────────────────

# A pre-transition hook: receives (asset, target_stage, context),
# returns True to allow the transition or False to block it.
PreTransitionHook = Callable[[PropertyAsset, PipelineStage, Dict[str, Any]], bool]


# ── Asset repository abstraction ─────────────────────────────────────────────


class AssetRepository(ABC):
    """Interface for reading and persisting PropertyAsset state."""

    @abstractmethod
    def load(self, asset_id: str) -> Optional[PropertyAsset]:
        """Load an asset by its identifier."""
        ...

    @abstractmethod
    def save(self, asset: PropertyAsset) -> None:
        """Persist an asset after a transition."""
        ...

    @abstractmethod
    def list_all(self) -> List[PropertyAsset]:
        """Return all known assets."""
        ...


class InMemoryAssetRepository(AssetRepository):
    """In-memory implementation for testing and single-process use."""

    def __init__(self) -> None:
        self._store: Dict[str, PropertyAsset] = {}

    def load(self, asset_id: str) -> Optional[PropertyAsset]:
        return self._store.get(asset_id)

    def save(self, asset: PropertyAsset) -> None:
        self._store[asset.asset_id] = asset.model_copy(deep=True)

    def list_all(self) -> List[PropertyAsset]:
        return [a.model_copy(deep=True) for a in self._store.values()]


# ── Pipeline engine ──────────────────────────────────────────────────────────


class PipelineEngine:
    """Pipeline runner that orchestrates transitions through hook evaluation.

    The engine evaluates all registered pre-transition hooks before allowing
    a stage change. If any hook rejects the transition (returns False), the
    asset is automatically redirected to PipelineStage.KILLED with the
    violation recorded in the stage log.

    Args:
        repository: An AssetRepository instance for loading/saving assets.
    """

    def __init__(self, repository: AssetRepository) -> None:
        self.repository = repository
        # Stage-keyed hook registry: {target_stage: [hook_fn, ...]}
        self._hooks: Dict[PipelineStage, List[PreTransitionHook]] = {}

    # ── Hook management ──────────────────────────────────────────────────────

    def register_hook(
        self,
        stage: PipelineStage,
        hook: PreTransitionHook,
    ) -> None:
        """Register a pre-transition hook for the given target stage.

        The hook will be called before any transition to *stage*. If the
        hook returns False, the transition is blocked and the asset is
        redirected to KILLED.

        Args:
            stage: The target pipeline stage to attach the hook to.
            hook: A callable accepting (asset, target_stage, context)
                  and returning True (allow) or False (block).
        """
        if stage not in self._hooks:
            self._hooks[stage] = []
        self._hooks[stage].append(hook)
        logger.debug(
            "Registered hook for %s (total: %d)",
            stage.value,
            len(self._hooks[stage]),
        )

    def remove_hook(
        self,
        stage: PipelineStage,
        hook: PreTransitionHook,
    ) -> None:
        """Remove a previously registered hook.

        Args:
            stage: The target stage the hook was registered for.
            hook: The hook function to remove.
        """
        if stage in self._hooks:
            self._hooks[stage] = [h for h in self._hooks[stage] if h is not hook]
            logger.debug("Removed hook for %s", stage.value)

    # ── Core transition logic ────────────────────────────────────────────────

    def process_transition(
        self,
        asset: PropertyAsset,
        target_stage: PipelineStage,
        context: Dict[str, Any],
    ) -> PropertyAsset:
        """Attempt to transition an asset to the target stage.

        Evaluation order:
          1. Fetch the latest asset state from the repository.
          2. Evaluate all hooks registered for *target_stage*.
          3. If all hooks pass → execute the transition via
             asset.transition_to() and persist.
          4. If ANY hook fails → redirect to KILLED, record the first
             violation reason in the log, and persist.

        Args:
            asset: The asset to transition. Its current_stage determines
                   which transitions are legal.
            target_stage: Desired next stage.
            context: Arbitrary key-value data passed to hooks and
                     recorded in the stage log metrics_snapshot.

        Returns:
            The updated PropertyAsset after the transition (or KILLED).

        Raises:
            InvalidStageTransitionException: If the raw transition is not
                allowed by the static ruleset (before hooks are evaluated).
        """
        # Reload from repo for consistency
        persisted = self.repository.load(asset.asset_id)
        working_asset = persisted if persisted is not None else asset

        # ── Pre-transition hook evaluation ──────────────────────────────
        violation = self._evaluate_hooks(working_asset, target_stage, context)

        if violation is not None:
            # Hook rejected the transition → redirect to KILLED
            logger.warning(
                "Hook blocked transition %s -> %s for asset %s: %s",
                working_asset.current_stage.value,
                target_stage.value,
                working_asset.asset_id,
                violation,
            )
            working_asset.transition_to(
                PipelineStage.KILLED,
                reason=violation,
                metrics=context,
            )
            self.repository.save(working_asset)
            return working_asset

        # ── All hooks passed → execute the transition ───────────────────
        working_asset.transition_to(
            target_stage,
            reason=context.get("reason"),
            metrics=context,
        )
        self.repository.save(working_asset)

        logger.info(
            "Asset %s transitioned %s -> %s",
            working_asset.asset_id,
            working_asset.stage_history[-2].stage.value
            if len(working_asset.stage_history) >= 2
            else "(start)",
            working_asset.current_stage.value,
        )
        return working_asset

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _evaluate_hooks(
        self,
        asset: PropertyAsset,
        target_stage: PipelineStage,
        context: Dict[str, Any],
    ) -> Optional[str]:
        """Evaluate all hooks for the target stage.

        Returns the first violation message if a hook rejects, or None
        if all hooks pass.
        """
        stage_hooks = self._hooks.get(target_stage, [])
        for hook in stage_hooks:
            try:
                result = hook(asset, target_stage, context)
            except Exception as exc:
                logger.error(
                    "Hook raised exception for asset %s -> %s: %s",
                    asset.asset_id,
                    target_stage.value,
                    exc,
                )
                return f"Hook exception: {exc}"

            if not result:
                # Extract a meaningful violation message from context or hook
                msg = context.get(
                    "violation_reason",
                    f"Pre-transition hook rejected {target_stage.value}",
                )
                return cast(str, msg)

        return None

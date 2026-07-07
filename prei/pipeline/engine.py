"""Pipeline engine for batch-processing assets through stage transitions.

Provides the PipelineEngine class with hook-based pre-transition evaluation,
a repository abstraction for asset persistence, SQLite-backed and transactional
repositories, and a state aggregator for UI summary statistics.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, cast

from prei.models.pipeline import (
    PipelineStage,
    PropertyAsset,
    StageLog,
)

logger = logging.getLogger(__name__)

# ── Type aliases ──────────────────────────────────────────────────────────────

PreTransitionHook = Callable[[PropertyAsset, PipelineStage, Dict[str, Any]], bool]


# ═══════════════════════════════════════════════════════════════════════════════
#  Asset repository abstraction
# ═══════════════════════════════════════════════════════════════════════════════


class AssetRepository(ABC):
    """Interface for reading and persisting PropertyAsset state.

    Subclasses may optionally override begin(), commit(), and rollback()
    to participate in atomic transactions. The base implementations are
    no-ops.
    """

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

    # ── Optional transaction hooks ────────────────────────────────────────────
    # Override in subclasses that support atomic transactions.

    def begin(self) -> None:
        """Begin a transaction (no-op by default)."""

    def commit(self) -> None:
        """Commit the current transaction (no-op by default)."""

    def rollback(self) -> None:
        """Roll back the current transaction (no-op by default)."""


# ═══════════════════════════════════════════════════════════════════════════════
#  In-memory repository (testing / single-process)
# ═══════════════════════════════════════════════════════════════════════════════


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


# ═══════════════════════════════════════════════════════════════════════════════
#  Transactional repository wrapper
# ═══════════════════════════════════════════════════════════════════════════════


class TransactionError(Exception):
    """Raised when a transaction operation fails."""


class TransactionalRepository(AssetRepository):
    """Thread-safe transactional wrapper around any AssetRepository.

    Wraps save() operations inside explicit begin/commit/rollback boundaries.
    If commit() fails, all saves since the last begin() are rolled back.

    Thread-safe: uses a per-instance lock to serialize concurrent access.
    """

    def __init__(self, inner: AssetRepository) -> None:
        self._inner = inner
        self._lock = threading.Lock()
        self._in_transaction = False
        self._pending: List[PropertyAsset] = []

    # ── Transaction lifecycle ─────────────────────────────────────────────────

    def begin(self) -> None:
        """Start a new transaction. All saves are buffered until commit()."""
        with self._lock:
            if self._in_transaction:
                raise TransactionError("Transaction already in progress")
            self._in_transaction = True
            self._pending.clear()
            self._inner.begin()

    def commit(self) -> None:
        """Flush all buffered saves to the inner repository atomically.

        If any single save fails, the entire batch is rolled back.
        """
        with self._lock:
            if not self._in_transaction:
                raise TransactionError("No transaction in progress")
            saved: List[PropertyAsset] = []
            try:
                for asset in self._pending:
                    self._inner.save(asset)
                    saved.append(asset)
                self._inner.commit()
                self._pending.clear()
                self._in_transaction = False
            except Exception:
                # Roll back: revert inner repository state
                logger.error("Transaction commit failed — rolling back")
                self._inner.rollback()
                self._pending.clear()
                self._in_transaction = False
                raise TransactionError("Transaction commit failed, rolled back")

    def rollback(self) -> None:
        """Abort the current transaction and discard all buffered saves."""
        with self._lock:
            if not self._in_transaction:
                raise TransactionError("No transaction in progress")
            self._inner.rollback()
            self._pending.clear()
            self._in_transaction = False
            logger.info("Transaction rolled back — %d pending saves discarded")

    # ── Repository interface ──────────────────────────────────────────────────

    def load(self, asset_id: str) -> Optional[PropertyAsset]:
        with self._lock:
            return self._inner.load(asset_id)

    def save(self, asset: PropertyAsset) -> None:
        with self._lock:
            if self._in_transaction:
                # Buffer — will be flushed on commit()
                self._pending.append(asset.model_copy(deep=True))
            else:
                # No active transaction — save directly
                self._inner.save(asset)

    def list_all(self) -> List[PropertyAsset]:
        with self._lock:
            return self._inner.list_all()


# ═══════════════════════════════════════════════════════════════════════════════
#  SQLite asset repository
# ═══════════════════════════════════════════════════════════════════════════════


class SqliteAssetRepository(AssetRepository):
    """SQLite-backed asset repository with full transaction support.

    Stores assets in a ``pipeline_assets`` table serialised as JSONB
    (JSON text column). Thread-safe via SQLite's built-in WAL mode.

    Args:
        db_path: Filesystem path to the SQLite database file.
        create_tables: If True (default), initialises the schema on connect.
    """

    def __init__(self, db_path: str, create_tables: bool = True) -> None:
        self._db_path = db_path
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._lock = threading.Lock()

        if create_tables:
            self._init_schema()

    def _init_schema(self) -> None:
        """Create the pipeline tables if they don't exist."""
        with self._lock:
            self._conn.executescript("""
                CREATE TABLE IF NOT EXISTS pipeline_assets (
                    asset_id        TEXT PRIMARY KEY,
                    address         TEXT NOT NULL,
                    current_stage   TEXT NOT NULL,
                    stage_history   TEXT NOT NULL DEFAULT '[]',
                    kill_reason     TEXT,
                    created_at      TEXT NOT NULL,
                    updated_at      TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_assets_stage
                    ON pipeline_assets(current_stage);
            """)
            self._conn.commit()

    # ── Transaction hooks ─────────────────────────────────────────────────────

    def begin(self) -> None:
        if self._conn.in_transaction:
            return  # already in a transaction — no-op to avoid nested begin
        self._conn.execute("BEGIN TRANSACTION;")

    def commit(self) -> None:
        self._conn.commit()

    def rollback(self) -> None:
        self._conn.rollback()

    # ── Repository interface ──────────────────────────────────────────────────

    def load(self, asset_id: str) -> Optional[PropertyAsset]:
        with self._lock:
            cursor = self._conn.execute(
                "SELECT * FROM pipeline_assets WHERE asset_id = ?",
                (asset_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return self._row_to_asset(row)

    def save(self, asset: PropertyAsset) -> None:
        with self._lock:
            now = datetime.now(timezone.utc).isoformat()
            history_json = json.dumps(
                [log.model_dump(mode="json") for log in asset.stage_history],
                default=str,
            )

            self._conn.execute(
                """INSERT OR REPLACE INTO pipeline_assets
                   (asset_id, address, current_stage, stage_history,
                    kill_reason, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, COALESCE(
                       (SELECT created_at FROM pipeline_assets
                        WHERE asset_id = ?), ?), ?)""",
                (
                    asset.asset_id,
                    asset.address,
                    asset.current_stage.value,
                    history_json,
                    asset.kill_reason,
                    asset.asset_id,  # for COALESCE subquery
                    now,  # created_at fallback
                    now,  # updated_at
                ),
            )

            # Flush to disk after each save outside explicit transactions
            if not self._conn.in_transaction:
                self._conn.commit()

    def list_all(self) -> List[PropertyAsset]:
        with self._lock:
            cursor = self._conn.execute(
                "SELECT * FROM pipeline_assets ORDER BY updated_at DESC"
            )
            return [self._row_to_asset(row) for row in cursor.fetchall()]

    # ── Internal helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _row_to_asset(row: sqlite3.Row) -> PropertyAsset:
        """Deserialise a database row into a PropertyAsset."""
        history_data = json.loads(row["stage_history"]) if row["stage_history"] else []
        stage_history = (
            [StageLog(**log) for log in history_data] if history_data else []
        )

        return PropertyAsset(
            asset_id=row["asset_id"],
            address=row["address"],
            current_stage=PipelineStage(row["current_stage"]),
            stage_history=stage_history,
            kill_reason=row["kill_reason"],
        )

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
#  State aggregator
# ═══════════════════════════════════════════════════════════════════════════════


class StateAggregator:
    """Compute summary statistics about asset pipeline distribution.

    Exposes counts and aggregates by pipeline stage for UI dashboards.

    Args:
        repository: An AssetRepository to query for asset data.
    """

    def __init__(self, repository: AssetRepository) -> None:
        self.repository = repository

    def count_by_stage(self) -> Dict[str, int]:
        """Return a mapping of stage name → asset count."""
        assets = self.repository.list_all()
        counts: Dict[str, int] = {}
        for a in assets:
            stage = a.current_stage.value
            counts[stage] = counts.get(stage, 0) + 1
        return counts

    def summary(self) -> Dict[str, Any]:
        """Return a full pipeline summary dict.

        Keys:
            total_assets (int): Total number of assets tracked.
            by_stage (dict): Stage name → count (only non-zero stages).
            pipeline_flow (dict): High-level pipeline phase counts.
            killed (int): Number of killed assets.
        """
        assets = self.repository.list_all()
        by_stage: Dict[str, int] = {}
        killed = 0
        for a in assets:
            stage = a.current_stage.value
            by_stage[stage] = by_stage.get(stage, 0) + 1
            if stage == PipelineStage.KILLED.value:
                killed += 1

        # High-level pipeline phases
        acquisition = sum(
            by_stage.get(s.value, 0)
            for s in [
                PipelineStage.GACS,
                PipelineStage.DISCOVERY,
                PipelineStage.SCREENING,
            ]
        )
        deal_making = sum(
            by_stage.get(s.value, 0)
            for s in [
                PipelineStage.UNDERWRITING,
                PipelineStage.OFFER,
                PipelineStage.DUE_DILIGENCE,
                PipelineStage.CLOSING,
            ]
        )
        operations = sum(
            by_stage.get(s.value, 0)
            for s in [
                PipelineStage.TURNOVER,
                PipelineStage.LEASING,
            ]
        )
        portfolio = by_stage.get(PipelineStage.PORTFOLIO.value, 0)

        return {
            "total_assets": len(assets),
            "by_stage": {k: v for k, v in sorted(by_stage.items())},
            "pipeline_flow": {
                "acquisition": acquisition,
                "deal_making": deal_making,
                "operations": operations,
                "portfolio": portfolio,
            },
            "killed": killed,
        }


# ═══════════════════════════════════════════════════════════════════════════════
#  Pipeline engine
# ═══════════════════════════════════════════════════════════════════════════════


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
        self._hooks: Dict[PipelineStage, List[PreTransitionHook]] = {}

    def register_hook(
        self,
        stage: PipelineStage,
        hook: PreTransitionHook,
    ) -> None:
        """Register a pre-transition hook for the given target stage."""
        if stage not in self._hooks:
            self._hooks[stage] = []
        self._hooks[stage].append(hook)

    def remove_hook(
        self,
        stage: PipelineStage,
        hook: PreTransitionHook,
    ) -> None:
        """Remove a previously registered hook."""
        if stage in self._hooks:
            self._hooks[stage] = [h for h in self._hooks[stage] if h is not hook]

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

        Returns:
            The updated PropertyAsset after the transition (or KILLED).

        Raises:
            InvalidStageTransitionException: If the raw transition is not
                allowed by the static ruleset (before hooks are evaluated).
        """
        persisted = self.repository.load(asset.asset_id)
        working_asset = persisted if persisted is not None else asset

        violation = self._evaluate_hooks(working_asset, target_stage, context)

        if violation is not None:
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
                msg = context.get(
                    "violation_reason",
                    f"Pre-transition hook rejected {target_stage.value}",
                )
                return cast(str, msg)

        return None

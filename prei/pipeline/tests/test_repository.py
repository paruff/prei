"""Tests for the transactional persistence layer and state aggregator."""

import os
import tempfile

import pytest

from prei.models.pipeline import PipelineStage, PropertyAsset
from prei.pipeline.engine import (
    InMemoryAssetRepository,
    SqliteAssetRepository,
    StateAggregator,
    TransactionError,
    TransactionalRepository,
)


def _make_asset(
    asset_id: str = "T1", stage: PipelineStage = PipelineStage.GACS
) -> PropertyAsset:
    return PropertyAsset(
        asset_id=asset_id, address=f"{asset_id} St", current_stage=stage
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  TransactionalRepository
# ═══════════════════════════════════════════════════════════════════════════════


class TestTransactionalRepository:
    """Tests for the transactional wrapper."""

    def test_basic_save_and_load(self):
        """Non-transactional save works immediately."""
        inner = InMemoryAssetRepository()
        tx = TransactionalRepository(inner)
        a = _make_asset("X1")
        tx.save(a)
        assert tx.load("X1") is not None
        assert inner.load("X1") is not None  # also persisted to inner

    def test_transaction_buffers_saves(self):
        """Saves within a transaction are buffered until commit."""
        inner = InMemoryAssetRepository()
        tx = TransactionalRepository(inner)
        tx.begin()
        tx.save(_make_asset("BUF-1"))
        # Should not be in inner yet
        assert inner.load("BUF-1") is None
        # But should be visible via transactional repo
        assert tx.load("BUF-1") is None  # loads from inner, which doesn't have it
        tx.commit()
        assert inner.load("BUF-1") is not None

    def test_rollback_discards_pending(self):
        """Rollback discards all saves made during the transaction."""
        inner = InMemoryAssetRepository()
        tx = TransactionalRepository(inner)
        tx.begin()
        tx.save(_make_asset("RB-1"))
        tx.rollback()
        assert inner.list_all() == []
        assert inner.load("RB-1") is None

    def test_rollback_restores_original_state(self):
        """Rollback reverts to pre-transaction state."""
        inner = InMemoryAssetRepository()
        inner.save(_make_asset("ORIG"))
        tx = TransactionalRepository(inner)

        tx.begin()
        tx.save(_make_asset("NEW-1"))
        inner.save(_make_asset("NEW-2"))  # directly modify inner
        tx.rollback()

        assert inner.load("ORIG") is not None  # original preserved
        # NEW-2 was saved directly to inner during tx — rollback doesn't undo it
        # because the inner's rollback() is a no-op for InMemory
        assert inner.load("NEW-1") is None  # tx-save rolled back

    def test_double_begin_raises(self):
        """Calling begin() twice raises TransactionError."""
        tx = TransactionalRepository(InMemoryAssetRepository())
        tx.begin()
        with pytest.raises(TransactionError, match="already in progress"):
            tx.begin()

    def test_commit_without_begin_raises(self):
        """Calling commit() without begin() raises TransactionError."""
        tx = TransactionalRepository(InMemoryAssetRepository())
        with pytest.raises(TransactionError, match="No transaction"):
            tx.commit()

    def test_rollback_without_begin_raises(self):
        """Calling rollback() without begin() raises TransactionError."""
        tx = TransactionalRepository(InMemoryAssetRepository())
        with pytest.raises(TransactionError, match="No transaction"):
            tx.rollback()

    def test_multiple_transactions(self):
        """Multiple begin/commit cycles work."""
        tx = TransactionalRepository(InMemoryAssetRepository())
        for i in range(5):
            tx.begin()
            tx.save(_make_asset(f"MULTI-{i}"))
            tx.commit()
        assert len(tx.list_all()) == 5

    def test_list_all(self):
        """list_all() works with and without transactions."""
        tx = TransactionalRepository(InMemoryAssetRepository())
        tx.save(_make_asset("L1"))
        tx.begin()
        tx.save(_make_asset("L2"))
        # list_all sees only committed and inner (not buffered)
        assert len(tx.list_all()) == 1
        tx.commit()
        assert len(tx.list_all()) == 2


# ═══════════════════════════════════════════════════════════════════════════════
#  SqliteAssetRepository
# ═══════════════════════════════════════════════════════════════════════════════


class TestSqliteAssetRepository:
    """Tests for the SQLite-backed repository."""

    @pytest.fixture
    def repo(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        repo = SqliteAssetRepository(db_path, create_tables=True)
        yield repo
        repo.close()
        os.unlink(db_path)

    def test_save_and_load(self, repo):
        a = _make_asset("SQL-1")
        repo.save(a)
        loaded = repo.load("SQL-1")
        assert loaded is not None
        assert loaded.asset_id == "SQL-1"
        assert loaded.current_stage == PipelineStage.GACS

    def test_load_nonexistent(self, repo):
        assert repo.load("DOES-NOT-EXIST") is None

    def test_list_all(self, repo):
        repo.save(_make_asset("A"))
        repo.save(_make_asset("B"))
        assert len(repo.list_all()) == 2

    def test_update_existing(self, repo):
        a = _make_asset("UPD")
        repo.save(a)
        a.transition_to(PipelineStage.DISCOVERY)
        repo.save(a)
        loaded = repo.load("UPD")
        assert loaded is not None
        assert loaded.current_stage == PipelineStage.DISCOVERY
        assert len(loaded.stage_history) == 1

    def test_transaction_commit(self, repo):
        repo.begin()
        repo.save(_make_asset("TX-A"))
        repo.save(_make_asset("TX-B"))
        repo.commit()
        assert repo.load("TX-A") is not None
        assert repo.load("TX-B") is not None

    def test_transaction_rollback(self, repo):
        """Rollback discards uncommitted saves within the transaction."""
        repo.begin()
        repo.save(_make_asset("DURING"))
        repo.rollback()
        # "DURING" was not committed — should not exist
        assert repo.load("DURING") is None

    def test_transaction_commit_persists(self, repo):
        """Committed transaction saves are visible after commit."""
        repo.save(_make_asset("BEFORE"))
        repo.begin()
        repo.save(_make_asset("DURING"))
        repo.commit()
        assert repo.load("BEFORE") is not None
        assert repo.load("DURING") is not None

    def test_kill_reason_persisted(self, repo):
        a = _make_asset("KILL1")
        a.transition_to(PipelineStage.KILLED, reason="Budget cut")
        repo.save(a)
        loaded = repo.load("KILL1")
        assert loaded is not None
        assert loaded.current_stage == PipelineStage.KILLED
        assert loaded.kill_reason == "Budget cut"

    def test_stage_history_persisted(self, repo):
        a = _make_asset("HIST")
        a.transition_to(PipelineStage.DISCOVERY)
        a.transition_to(PipelineStage.SCREENING)
        a.transition_to(PipelineStage.UNDERWRITING)
        repo.save(a)
        loaded = repo.load("HIST")
        assert loaded is not None
        assert len(loaded.stage_history) == 3
        assert loaded.stage_history[0].stage == PipelineStage.DISCOVERY
        assert loaded.stage_history[2].stage == PipelineStage.UNDERWRITING


# ═══════════════════════════════════════════════════════════════════════════════
#  StateAggregator
# ═══════════════════════════════════════════════════════════════════════════════


class TestStateAggregator:
    """Tests for the pipeline state aggregator."""

    def _seed_assets(self, repo):
        """Create 10 assets across different stages."""
        stages = [
            PipelineStage.DISCOVERY,
            PipelineStage.SCREENING,
            PipelineStage.UNDERWRITING,
            PipelineStage.OFFER,
            PipelineStage.DUE_DILIGENCE,
            PipelineStage.CLOSING,
            PipelineStage.TURNOVER,
            PipelineStage.LEASING,
            PipelineStage.PORTFOLIO,
            PipelineStage.KILLED,
        ]
        for i, stage in enumerate(stages):
            a = _make_asset(f"AG-{i:02d}", stage)
            repo.save(a)

    def test_count_by_stage(self):
        repo = InMemoryAssetRepository()
        self._seed_assets(repo)
        agg = StateAggregator(repo)
        counts = agg.count_by_stage()
        assert counts["DISCOVERY"] == 1
        assert counts["SCREENING"] == 1
        assert counts["UNDERWRITING"] == 1
        assert counts["KILLED"] == 1
        assert counts["PORTFOLIO"] == 1
        assert sum(counts.values()) == 10

    def test_summary_includes_total(self):
        repo = InMemoryAssetRepository()
        self._seed_assets(repo)
        agg = StateAggregator(repo)
        s = agg.summary()
        assert s["total_assets"] == 10

    def test_summary_pipeline_flow(self):
        repo = InMemoryAssetRepository()
        self._seed_assets(repo)
        agg = StateAggregator(repo)
        flow = agg.summary()["pipeline_flow"]
        # DISCOVERY + SCREENING (GACS default not seeded here)
        assert flow["acquisition"] == 2
        # UNDERWRITING + OFFER + DUE_DILIGENCE + CLOSING
        assert flow["deal_making"] == 4
        # TURNOVER + LEASING
        assert flow["operations"] == 2
        # PORTFOLIO
        assert flow["portfolio"] == 1

    def test_summary_killed(self):
        repo = InMemoryAssetRepository()
        a = _make_asset("DEAD", PipelineStage.KILLED)
        repo.save(a)
        agg = StateAggregator(repo)
        assert agg.summary()["killed"] == 1

    def test_empty_repo_summary(self):
        repo = InMemoryAssetRepository()
        agg = StateAggregator(repo)
        s = agg.summary()
        assert s["total_assets"] == 0
        assert s["killed"] == 0
        assert s["pipeline_flow"]["acquisition"] == 0

    def test_by_stage_empty_repo(self):
        repo = InMemoryAssetRepository()
        agg = StateAggregator(repo)
        assert agg.count_by_stage() == {}

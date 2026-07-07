"""Tests for the PipelineEngine and hook execution."""

from prei.models.pipeline import PipelineStage, PropertyAsset
from prei.pipeline.engine import (
    InMemoryAssetRepository,
    PipelineEngine,
)


class TestHookFunctions:
    """Test suite for PipelineEngine hook registration and evaluation."""

    def _make_asset(self, asset_id: str = "ASSET-001") -> PropertyAsset:
        return PropertyAsset(asset_id=asset_id, address="123 Main St")

    def _make_engine(self) -> PipelineEngine:
        repo = InMemoryAssetRepository()
        return PipelineEngine(repository=repo)

    # ── Basic forward flow ───────────────────────────────────────────────────

    def test_basic_forward_transition(self):
        """Full forward pipeline without hooks."""
        engine = self._make_engine()
        asset = self._make_asset()
        engine.repository.save(asset)

        expected_stages = [
            PipelineStage.DISCOVERY,
            PipelineStage.SCREENING,
            PipelineStage.UNDERWRITING,
            PipelineStage.OFFER,
            PipelineStage.DUE_DILIGENCE,
            PipelineStage.CLOSING,
            PipelineStage.TURNOVER,
            PipelineStage.LEASING,
            PipelineStage.PORTFOLIO,
        ]

        for target in expected_stages:
            asset = engine.process_transition(
                asset, target, {"reason": f"Moving to {target.value}"}
            )
            assert asset.current_stage == target, (
                f"Expected {target.value}, got {asset.current_stage.value}"
            )

        assert asset.current_stage == PipelineStage.PORTFOLIO
        assert len(asset.stage_history) == 9  # GACS → PORTFOLIO = 9 transitions

    # ── Hook acceptance ──────────────────────────────────────────────────────

    def test_hook_allows_transition(self):
        """If hook returns True, the transition proceeds normally."""
        engine = self._make_engine()
        asset = self._make_asset()
        engine.repository.save(asset)

        def allow_all(a, t, c):
            return True

        engine.register_hook(PipelineStage.DISCOVERY, allow_all)
        asset = engine.process_transition(asset, PipelineStage.DISCOVERY, {})
        assert asset.current_stage == PipelineStage.DISCOVERY

    # ── Hook rejection → KILLED ──────────────────────────────────────────────

    def test_hook_rejection_redirects_to_killed(self):
        """If hook returns False, asset is redirected to KILLED with reason."""
        engine = self._make_engine()
        asset = self._make_asset()
        engine.repository.save(asset)

        def reject_deals(a, t, c):
            return False

        engine.register_hook(PipelineStage.DISCOVERY, reject_deals)
        asset = engine.process_transition(
            asset,
            PipelineStage.DISCOVERY,
            {"violation_reason": "Not in target market"},
        )

        assert asset.current_stage == PipelineStage.KILLED
        assert asset.kill_reason == "Not in target market"

    def test_hook_rejection_logged_in_history(self):
        """KILLED transition is recorded in stage_history with reason."""
        engine = self._make_engine()
        asset = self._make_asset()
        engine.repository.save(asset)

        def reject(a, t, c):
            return False

        engine.register_hook(PipelineStage.UNDERWRITING, reject)
        asset = engine.process_transition(
            asset, PipelineStage.DISCOVERY, {"reason": "Moving along"}
        )
        assert asset.current_stage == PipelineStage.DISCOVERY

        asset = engine.process_transition(
            asset, PipelineStage.SCREENING, {"reason": "Looks good"}
        )
        assert asset.current_stage == PipelineStage.SCREENING

        asset = engine.process_transition(
            asset,
            PipelineStage.UNDERWRITING,
            {"violation_reason": "Cap rate too low", "cap_rate": 0.04},
        )
        assert asset.current_stage == PipelineStage.KILLED
        assert asset.kill_reason == "Cap rate too low"

        # Verify the KILLED transition is the last entry in stage_history
        last_log = asset.stage_history[-1]
        assert last_log.stage == PipelineStage.KILLED
        assert last_log.reason == "Cap rate too low"
        assert last_log.metrics_snapshot["cap_rate"] == 0.04

    # ── Multiple hooks per stage ─────────────────────────────────────────────

    def test_multiple_hooks_all_pass(self):
        """All hooks must pass for transition to proceed."""
        engine = self._make_engine()
        asset = self._make_asset()
        engine.repository.save(asset)

        call_order: list[int] = []

        def hook1(a, t, c):
            call_order.append(1)
            return True

        def hook2(a, t, c):
            call_order.append(2)
            return True

        def hook3(a, t, c):
            call_order.append(3)
            return True

        engine.register_hook(PipelineStage.DISCOVERY, hook1)
        engine.register_hook(PipelineStage.DISCOVERY, hook2)
        engine.register_hook(PipelineStage.DISCOVERY, hook3)

        asset = engine.process_transition(asset, PipelineStage.DISCOVERY, {})
        assert asset.current_stage == PipelineStage.DISCOVERY
        assert call_order == [1, 2, 3]

    def test_multiple_hooks_first_failure_stops(self):
        """If first hook fails, engine returns KILLED and stops evaluation."""
        engine = self._make_engine()
        asset = self._make_asset()
        engine.repository.save(asset)

        call_order: list[int] = []

        def hook_fail(a, t, c):
            call_order.append(1)
            return False

        def hook_never_reached(a, t, c):
            call_order.append(2)
            return True

        engine.register_hook(PipelineStage.DISCOVERY, hook_fail)
        engine.register_hook(PipelineStage.DISCOVERY, hook_never_reached)

        asset = engine.process_transition(
            asset,
            PipelineStage.DISCOVERY,
            {"violation_reason": "Hook 1 failed"},
        )
        assert asset.current_stage == PipelineStage.KILLED
        # Engine short-circuits on first failure — hook2 never runs
        assert call_order == [1]

    # ── Hook exception handling ──────────────────────────────────────────────

    def test_hook_exception_redirects_to_killed(self):
        """If a hook raises an exception, asset is redirected to KILLED."""
        engine = self._make_engine()
        asset = self._make_asset()
        engine.repository.save(asset)

        def broken_hook(a, t, c):
            raise ValueError("Something went wrong")

        engine.register_hook(PipelineStage.DISCOVERY, broken_hook)
        asset = engine.process_transition(asset, PipelineStage.DISCOVERY, {})

        assert asset.current_stage == PipelineStage.KILLED
        assert "Hook exception" in (asset.kill_reason or "")
        assert "Something went wrong" in (asset.kill_reason or "")

    # ── Hook removal ─────────────────────────────────────────────────────────

    def test_remove_hook(self):
        """After removing a hook, it no longer affects transitions."""
        engine = self._make_engine()
        asset = self._make_asset()
        engine.repository.save(asset)

        def reject(a, t, c):
            return False

        engine.register_hook(PipelineStage.DISCOVERY, reject)
        engine.remove_hook(PipelineStage.DISCOVERY, reject)

        asset = engine.process_transition(asset, PipelineStage.DISCOVERY, {})
        assert asset.current_stage == PipelineStage.DISCOVERY

    # ── No hooks registered → transition proceeds ────────────────────────────

    def test_no_hooks_still_allows_transition(self):
        """With no hooks registered, transitions proceed unimpeded."""
        engine = self._make_engine()
        asset = self._make_asset()
        engine.repository.save(asset)

        asset = engine.process_transition(asset, PipelineStage.DISCOVERY, {})
        assert asset.current_stage == PipelineStage.DISCOVERY

    # ── InMemoryAssetRepository ──────────────────────────────────────────────

    def test_in_memory_repo_round_trip(self):
        """Save then load returns an equivalent (deep-copied) asset."""
        repo = InMemoryAssetRepository()
        asset = self._make_asset("ROUND-TRIP-001")
        asset.transition_to(PipelineStage.DISCOVERY, reason="test")
        repo.save(asset)

        loaded = repo.load("ROUND-TRIP-001")
        assert loaded is not None
        assert loaded.asset_id == "ROUND-TRIP-001"
        assert loaded.current_stage == PipelineStage.DISCOVERY
        assert len(loaded.stage_history) == 1
        # Verify deep copy independence
        loaded.transition_to(PipelineStage.SCREENING)
        assert asset.current_stage == PipelineStage.DISCOVERY  # original unchanged

    def test_in_memory_repo_list_all(self):
        """list_all returns all saved assets."""
        repo = InMemoryAssetRepository()
        a1 = self._make_asset("A1")
        a2 = self._make_asset("A2")
        repo.save(a1)
        repo.save(a2)
        assert len(repo.list_all()) == 2

    # ── KILLED is terminal ───────────────────────────────────────────────────

    def test_killed_is_terminal(self):
        """Engine raises InvalidStageTransitionException when trying to
        transition out of KILLED."""
        import pytest

        engine = self._make_engine()
        asset = self._make_asset()
        engine.repository.save(asset)

        from prei.models.pipeline import InvalidStageTransitionException

        # Go directly to KILLED
        asset = engine.process_transition(
            asset,
            PipelineStage.KILLED,
            {"reason": "Project cancelled"},
        )
        assert asset.current_stage == PipelineStage.KILLED

        # Try to leave KILLED
        with pytest.raises(InvalidStageTransitionException):
            engine.process_transition(asset, PipelineStage.DISCOVERY, {})

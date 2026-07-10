"""Tests for the pipeline lifecycle service (core/services/pipeline.py).

Covers:
  - _get_stage_index: stage ordering
  - advance_stage: stage progression, boundary conditions
  - kill_property: kill workflow
  - hold_property / reactivate_property: hold/reactivate workflow
  - get_source_record: source model resolution
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils.timezone import now as timezone_now

from core.models import PipelineProperty
from core.services.pipeline import (
    _get_stage_index,
    advance_stage,
    get_source_record,
    hold_property,
    kill_property,
    reactivate_property,
)


# ── _get_stage_index ─────────────────────────────────────────────────


class TestGetStageIndex:
    def test_valid_stage(self) -> None:
        assert _get_stage_index("DISCOVERED") == 0
        assert _get_stage_index("SCREENING") == 1
        assert _get_stage_index("STABILIZED") == 8

    def test_unknown_stage(self) -> None:
        with pytest.raises(ValueError, match="Unknown stage"):
            _get_stage_index("NONEXISTENT")


# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def pipeline_prop(db, django_user_model) -> PipelineProperty:
    user = django_user_model.objects.create_user(
        username="pipeuser", password="testpass1234"
    )
    return PipelineProperty.objects.create(
        user=user,
        source_type="manual",
        source_id="1",
        stage=PipelineProperty.Stage.DISCOVERED,
        status=PipelineProperty.Status.ACTIVE,
    )


@pytest.fixture
def killed_prop(pipeline_prop: PipelineProperty) -> PipelineProperty:
    pipeline_prop.status = PipelineProperty.Status.KILLED
    pipeline_prop.save(update_fields=["status"])
    return pipeline_prop


@pytest.fixture
def on_hold_prop(pipeline_prop: PipelineProperty) -> PipelineProperty:
    pipeline_prop.status = PipelineProperty.Status.ON_HOLD
    pipeline_prop.save(update_fields=["status"])
    return pipeline_prop


# ── advance_stage ────────────────────────────────────────────────────


class TestAdvanceStage:
    def test_advance_from_discovered_to_screening(
        self, pipeline_prop: PipelineProperty
    ) -> None:
        """DISCOVERED -> SCREENING."""
        result = advance_stage(pipeline_prop)
        assert result.stage == "SCREENING"
        assert result.screening_at is not None

    def test_advance_through_full_cycle(
        self, pipeline_prop: PipelineProperty
    ) -> None:
        """ADvance through all 9 stages to STABILIZED."""
        prop = pipeline_prop
        expected_stages = [
            "SCREENING",
            "UNDERWRITING",
            "OFFER",
            "DUE_DILIGENCE",
            "CLOSING",
            "ACQUIRED",
            "RENOVATION",
            "STABILIZED",
        ]
        for expected in expected_stages:
            prop = advance_stage(prop)
            assert prop.stage == expected

    def test_cannot_advance_from_stabilized(
        self, pipeline_prop: PipelineProperty
    ) -> None:
        """STABILIZED is the final stage — cannot advance further."""
        pipeline_prop.stage = PipelineProperty.Stage.STABILIZED
        pipeline_prop.save(update_fields=["stage"])
        with pytest.raises(ValueError, match="already at final stage"):
            advance_stage(pipeline_prop)

    def test_cannot_advance_killed_property(
        self, killed_prop: PipelineProperty
    ) -> None:
        """KILLED properties cannot advance."""
        with pytest.raises(ValueError, match="KILLED"):
            advance_stage(killed_prop)

    def test_cannot_advance_hold_property(
        self, on_hold_prop: PipelineProperty
    ) -> None:
        """ON_HOLD properties cannot advance."""
        with pytest.raises(ValueError, match="ON_HOLD"):
            advance_stage(on_hold_prop)

    def test_advance_sets_timestamp(self, pipeline_prop: PipelineProperty) -> None:
        """Advancing sets the timestamp for the new stage."""
        before = timezone_now() - timedelta(seconds=1)
        prop = advance_stage(pipeline_prop)
        after = timezone_now() + timedelta(seconds=1)
        assert prop.screening_at is not None
        assert before <= prop.screening_at <= after


# ── kill_property ────────────────────────────────────────────────────


class TestKillProperty:
    def test_kill_sets_status_and_reason(
        self, pipeline_prop: PipelineProperty
    ) -> None:
        """Kill sets KILLED status and records the reason."""
        result = kill_property(pipeline_prop, "Price out of range")
        assert result.status == "KILLED"
        assert result.kill_reason == "Price out of range"

    def test_kill_keeps_current_stage(
        self, pipeline_prop: PipelineProperty
    ) -> None:
        """Kill preserves the current stage."""
        result = kill_property(pipeline_prop, "Condition issues")
        assert result.stage == "DISCOVERED"

    def test_kill_without_reason(self, pipeline_prop: PipelineProperty) -> None:
        """Kill with empty reason is allowed."""
        result = kill_property(pipeline_prop, "")
        assert result.status == "KILLED"
        assert result.kill_reason == ""


# ── hold_property ────────────────────────────────────────────────────


class TestHoldProperty:
    def test_hold_sets_status(self, pipeline_prop: PipelineProperty) -> None:
        """Hold sets ON_HOLD status."""
        result = hold_property(pipeline_prop, "Waiting for inspection")
        assert result.status == "ON_HOLD"

    def test_hold_records_reason(
        self, pipeline_prop: PipelineProperty
    ) -> None:
        """Hold stores the reason."""
        result = hold_property(pipeline_prop, "Need more data")
        assert result.kill_reason == "Need more data"

    def test_hold_without_reason(
        self, pipeline_prop: PipelineProperty
    ) -> None:
        """Hold without reason sets kill_reason to blank (not overwritten)."""
        pipeline_prop.kill_reason = "old reason"
        pipeline_prop.save(update_fields=["kill_reason"])
        result = hold_property(pipeline_prop)
        assert result.status == "ON_HOLD"
        assert result.kill_reason == "old reason"  # not overwritten when reason is empty

    def test_hold_preserves_stage(
        self, pipeline_prop: PipelineProperty
    ) -> None:
        """Hold does NOT change the stage."""
        pipeline_prop.stage = PipelineProperty.Stage.UNDERWRITING
        pipeline_prop.save(update_fields=["stage"])
        result = hold_property(pipeline_prop)
        assert result.stage == "UNDERWRITING"


# ── reactivate_property ──────────────────────────────────────────────


class TestReactivateProperty:
    def test_reactivate_from_killed(
        self, killed_prop: PipelineProperty
    ) -> None:
        """KILLED property reactivates to ACTIVE."""
        result = reactivate_property(killed_prop)
        assert result.status == "ACTIVE"

    def test_reactivate_from_hold(
        self, on_hold_prop: PipelineProperty
    ) -> None:
        """ON_HOLD property reactivates to ACTIVE."""
        result = reactivate_property(on_hold_prop)
        assert result.status == "ACTIVE"

    def test_reactivate_preserves_stage(
        self, killed_prop: PipelineProperty
    ) -> None:
        """Reactivate does NOT change the stage."""
        result = reactivate_property(killed_prop)
        assert result.stage == "DISCOVERED"


# ── get_source_record ────────────────────────────────────────────────


class TestGetSourceRecord:
    def test_manual_source_returns_none(
        self, pipeline_prop: PipelineProperty
    ) -> None:
        """Manual source type returns None (no FK to resolve)."""
        result = get_source_record(pipeline_prop)
        assert result is None

    def test_unknown_source_returns_none(
        self, pipeline_prop: PipelineProperty
    ) -> None:
        """Unrecognised source type returns None."""
        pipeline_prop.source_type = "extraterrestrial"
        result = get_source_record(pipeline_prop)
        assert result is None

"""Shared fixtures for BDD acceptance tests.

The _reset_ctx fixture ensures shared state (PipelineCtx) is cleared
between scenarios, preventing stale object references from previous
tests that were rolled back at the database level.
"""

from __future__ import annotations

import pytest

from tests_bdd.steps.pipeline_acceptance_steps import _ctx


@pytest.fixture(autouse=True)
def _reset_ctx(db: None) -> None:
    """Reset shared state before each scenario.

    Runs inside the test database transaction (via ``db`` dependency)
    so that any database cleanup is atomic.  The primary purpose is
    clearing :class:`~tests_bdd.steps.pipeline_acceptance_steps.PipelineCtx`
    so that stale Python object references (pointing to rolled-back
    database rows) are not reused in a subsequent test.
    """
    _ctx.__init__()

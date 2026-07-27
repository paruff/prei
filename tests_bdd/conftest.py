"""Shared fixtures for BDD acceptance tests.

The _reset_ctx fixture ensures shared state (PipelineCtx) is cleared
between scenarios, preventing stale object references from previous
tests that were rolled back at the database level.
"""

from __future__ import annotations

import pytest

from tests_bdd.steps.pipeline_acceptance_steps import _ctx


@pytest.fixture(autouse=True)
def _reset_ctx(transactional_db: None) -> None:
    """Reset shared state before each scenario.

    Uses ``transactional_db`` (not ``db``) because pipeline_acceptance
    scenarios drive requests through pytest-django's ``live_server``
    fixture: the live server runs in a background thread with its own
    DB connection, so data created by a step only becomes visible to
    it once committed — a plain ``db``-wrapped transaction would hide
    it. Cleanup here is a manual reset (not an automatic rollback), so
    each scenario is responsible for its own DB state.  The primary
    purpose is clearing
    :class:`~tests_bdd.steps.pipeline_acceptance_steps.PipelineCtx` so
    that stale Python object references are not reused in a subsequent
    test.
    """
    _ctx.__init__()

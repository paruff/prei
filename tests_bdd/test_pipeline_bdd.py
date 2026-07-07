"""BDD test runner for pipeline.feature."""

from pytest_bdd import scenario
from tests_bdd.steps.pipeline_steps import *  # noqa: F401,F403 — step definitions


@scenario("features/pipeline.feature", "Discovery normalizes messy MLS data")
def test_bdd_discovery_normalizes_mls():
    pass


@scenario("features/pipeline.feature", "Duplicate address detected and skipped")
def test_bdd_duplicate_skipped():
    pass


@scenario("features/pipeline.feature", "Screening rejects low-yield properties")
def test_bdd_screening_yield():
    pass


@scenario("features/pipeline.feature", "Batch screening processes mixed properties")
def test_bdd_batch_screening():
    pass


@scenario("features/pipeline.feature", "Underwriting computes correct MAO")
def test_bdd_underwriting_mao():
    pass

"""Runner for journey.feature: steps 1-4 over HTTP against the seeded container."""

import pytest
from pytest_bdd import scenarios
from tests_bdd.steps.journey_steps import *  # noqa: F401,F403

pytestmark = pytest.mark.acceptance

scenarios("features/journey.feature")

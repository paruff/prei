"""End-to-end smoke test: build the Docker image, run the container, and
verify it serves pages.

These tests are marked ``@pytest.mark.e2e`` and are **skipped automatically**
when Docker is not available on the host.  Run them explicitly with::

    python -m pytest tests/test_docker_e2e.py -v --tb=long

or include them with::

    python -m pytest -m e2e

The test builds the image fresh via ``docker compose build``, starts a container
via ``docker run`` (using a non-default host port so it does not conflict with
any already-running ``prei`` instance), waits for the health endpoint to
respond, and then issues HTTP requests against the running service.

All containers are cleaned up in ``finalizer`` — even if assertions fail.
"""

from __future__ import annotations

import http.client
import json
import logging
import shutil
import subprocess
import time
import urllib.request

import pytest

logger = logging.getLogger(__name__)

# The host may already have prei running on port 8000, so we use a different
# host port for the e2e test container.
HOST_PORT = 8001
CONTAINER_PORT = 8000
IMAGE_TAG = "ghcr.io/paruff/prei:latest"
CONTAINER_NAME = "prei-e2e-test"

HEALTH_URL = f"http://localhost:{HOST_PORT}/api/health/"
ROOT_URL = f"http://localhost:{HOST_PORT}/"
LOGIN_URL = f"http://localhost:{HOST_PORT}/accounts/login/"

# Give the container up to 120 s to start (compose healthcheck start_period is
# 90 s, so 120 s gives 30 s of extra buffer for cold-start image building).
HEALTH_POLL_INTERVAL = 5
HEALTH_TIMEOUT = 120


# ---------------------------------------------------------------------------
# Marker registration (declared in pytest.ini)
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.e2e


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _docker_available() -> bool:
    """Return True if ``docker`` is on PATH and responding."""
    if shutil.which("docker") is None:
        return False
    try:
        subprocess.run(["docker", "info"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def _compose(*args: str) -> None:
    """Run ``docker compose -f <compose_file> <args>``."""
    cmd = ["docker", "compose", "-f", "docker-compose.yml", *args]
    logger.info("Running: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(
            "Command failed (exit %s):\nstderr:\n%s\nstdout:\n%s",
            result.returncode,
            result.stderr,
            result.stdout,
        )
        result.check_returncode()


def _docker_run() -> subprocess.CompletedProcess:
    """Start a detached container from the built image.

    Uses a non-default host port so it does not conflict with any
    already-running ``prei`` container.
    """
    cmd = [
        "docker",
        "run",
        "--rm",
        "-d",
        "--name",
        CONTAINER_NAME,
        "-p",
        f"{HOST_PORT}:{CONTAINER_PORT}",
        "--env-file",
        ".env",
        "-e",
        "RUN_MIGRATIONS=1",
        IMAGE_TAG,
    ]
    logger.info("Running: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(
            "docker run failed (exit %s):\nstderr:\n%s\nstdout:\n%s",
            result.returncode,
            result.stderr,
            result.stdout,
        )
        result.check_returncode()
    return result


def _docker_stop() -> None:
    """Stop and remove the e2e test container (best-effort)."""
    logger.info("Stopping container %s ...", CONTAINER_NAME)
    subprocess.run(
        ["docker", "rm", "-f", CONTAINER_NAME],
        capture_output=True,
    )
    logger.info("Container %s stopped.", CONTAINER_NAME)


def _wait_for_health(url: str = HEALTH_URL, timeout: int = HEALTH_TIMEOUT) -> None:
    """Poll *url* until it returns 200 or *timeout* seconds elapse."""
    deadline = time.monotonic() + timeout
    last_exc: Exception | None = None
    while time.monotonic() < deadline:
        try:
            resp = urllib.request.urlopen(url, timeout=10)
            if resp.status == 200:
                body = json.loads(resp.read().decode())
                assert body.get("status") == "ok", (
                    f"Health endpoint returned unexpected body: {body}"
                )
                elapsed = HEALTH_TIMEOUT - (deadline - time.monotonic())
                logger.info("Container healthy after %.0f s", elapsed)
                return
        except (
            urllib.error.URLError,
            ConnectionResetError,
            ConnectionRefusedError,
            OSError,
        ) as exc:
            last_exc = exc
            logger.debug("Health poll failed: %s", exc)
        time.sleep(HEALTH_POLL_INTERVAL)

    # Timed out — try one last HTTP request and show the response
    try:
        conn = http.client.HTTPConnection("localhost", HOST_PORT, timeout=10)
        conn.request("GET", "/api/health/")
        resp = conn.getresponse()
        body = resp.read().decode()
        logger.error("Final health attempt: %s %s — %s", resp.status, resp.reason, body)
    except Exception as exc:
        logger.error("Final health attempt also failed: %s", exc)

    raise TimeoutError(
        f"Container did not become healthy within {timeout} s. Last error: {last_exc}"
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def docker_container():
    """Build the image, start the container, yield, then tear down."""
    if not _docker_available():
        pytest.skip("Docker is not available on this host")

    # Ensure no leftover container from a previous failed run
    _docker_stop()

    # Build the image
    logger.info("Building Docker image ...")
    _compose("build", "--quiet")

    # Start the container
    logger.info("Starting container on port %s ...", HOST_PORT)
    _docker_run()

    yield  # tests run here

    # Teardown
    _docker_stop()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDockerContainerSmoke:
    """Verify the built container actually starts and serves pages."""

    def test_container_becomes_healthy(self, docker_container) -> None:
        """Container must pass its health check within the timeout."""
        _wait_for_health()

    def test_root_returns_200_or_302(self, docker_container) -> None:
        """GET / must not refuse the connection (200 or redirect)."""
        _wait_for_health()
        conn = http.client.HTTPConnection("localhost", HOST_PORT, timeout=10)
        conn.request("GET", "/")
        resp = conn.getresponse()
        resp.read()  # consume the response body
        assert resp.status in (
            200,
            302,
            301,
        ), f"GET / returned {resp.status} {resp.reason}"

    def test_login_page_returns_200(self, docker_container) -> None:
        """GET /accounts/login/ must serve the login form."""
        _wait_for_health()
        conn = http.client.HTTPConnection("localhost", HOST_PORT, timeout=10)
        conn.request("GET", "/accounts/login/")
        resp = conn.getresponse()
        body = resp.read().decode()
        assert resp.status == 200, (
            f"GET /accounts/login/ returned {resp.status} {resp.reason}"
        )
        # Verify we got actual HTML content, not an error page
        assert (
            "csrf" in body.lower()
            or "login" in body.lower()
            or "password" in body.lower()
        ), "Response does not look like a login page"

    def test_api_health_returns_json(self, docker_container) -> None:
        """GET /api/health/ must return JSON with status: ok."""
        _wait_for_health()
        conn = http.client.HTTPConnection("localhost", HOST_PORT, timeout=10)
        conn.request("GET", "/api/health/")
        resp = conn.getresponse()
        body = json.loads(resp.read().decode())
        assert resp.status == 200
        assert body.get("status") == "ok"

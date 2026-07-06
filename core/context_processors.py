"""
Context processor to provide version and environment info to all templates.

Sources (in priority order):
1. VERSION file at project root — the release source of truth
2. ``git describe --always --dirty`` — fallback for dev snapshot
3. ``/app/VERSION`` inside Docker — for containerized builds

Exposed template variables:
- ``version`` — e.g. "0.2.2"
- ``git_commit`` — short SHA, e.g. "a1b2c3d" or "a1b2c3d-dirty"
- ``api_keys_configured`` — bool, True when both CENSUS_API_KEY and BLS_API_KEY are set
- ``census_key_configured`` — bool
- ``bls_key_configured`` — bool
"""

from __future__ import annotations

import logging
import subprocess  # noqa: S404 — controlled use for git metadata only
from os import getenv
from pathlib import Path

logger = logging.getLogger("prei.config")


def _read_version() -> str:
    """Read version from VERSION file, falling back to git describe."""
    # Try VERSION file (project root and Docker container paths)
    for path in (
        Path(__file__).resolve().parent.parent / "VERSION",
        Path("/app/VERSION"),
    ):
        try:
            text = path.read_text().strip()
            if text:
                return text
        except (FileNotFoundError, OSError):
            continue

    # Fallback: git describe --always --dirty
    try:
        result = subprocess.run(
            ["git", "describe", "--always", "--dirty"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=Path(__file__).resolve().parent.parent,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.SubprocessError) as exc:
        logger.debug("git describe failed: %s", exc)

    return "0.0.0-dev"


def _read_git_commit() -> str:
    """Read short git commit SHA + dirty flag."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=Path(__file__).resolve().parent.parent,
        )
        if result.returncode == 0 and result.stdout.strip():
            sha = result.stdout.strip()
            # Check dirty
            dirty = subprocess.run(
                ["git", "diff", "--quiet"],
                cwd=Path(__file__).resolve().parent.parent,
                capture_output=True,
                timeout=5,
            )
            return f"{sha}-dirty" if dirty.returncode != 0 else sha
    except (FileNotFoundError, subprocess.SubprocessError) as exc:
        logger.debug("git rev-parse failed: %s", exc)
    return "unknown"


def version(request):  # type: ignore[no-untyped-def]
    """Add version, git_commit, and api key status to every template context."""
    census_key = getenv("CENSUS_API_KEY", "")
    bls_key = getenv("BLS_API_KEY", "")

    return {
        "version": _read_version(),
        "git_commit": _read_git_commit(),
        "api_keys_configured": bool(census_key and bls_key),
        "census_key_configured": bool(census_key),
        "bls_key_configured": bool(bls_key),
    }

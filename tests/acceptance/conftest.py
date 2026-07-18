"""Shared fixtures for HTTP acceptance tests.

Tests make real HTTP requests to a deployed application (local Docker
container, staging URL, or production URL).  No Django test client.
"""

from __future__ import annotations

import os

import httpx
import pytest


@pytest.fixture(scope="session")
def base_url() -> str:
    """Base URL of the deployed application.

    Set via ``BASE_URL`` environment variable.  Defaults to local development
    Docker container.
    """
    return os.environ.get("BASE_URL", "http://localhost:8000")


@pytest.fixture(scope="session")
def client(base_url: str) -> httpx.Client:
    """Pre-configured httpx client with base URL and 30-second timeout."""
    return httpx.Client(base_url=base_url, timeout=30, follow_redirects=False)

"""Regression tests for production hardening in Django settings."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_debug_false_enforces_secure_defaults() -> None:
    """Ensure secure defaults are enabled whenever DEBUG is false."""
    values = _load_settings_with_env({"DJANGO_ENV": "development", "DEBUG": "False"})

    assert values["ALLOWED_HOSTS"] == ["localhost", "127.0.0.1"]
    assert values["SECURE_SSL_REDIRECT"] is True
    assert values["SESSION_COOKIE_SECURE"] is True
    assert values["CSRF_COOKIE_SECURE"] is True
    assert values["SECURE_HSTS_SECONDS"] == 31536000
    assert values["SECURE_HSTS_INCLUDE_SUBDOMAINS"] is True
    assert values["X_FRAME_OPTIONS"] == "DENY"


def test_whitenoise_and_static_storage_are_configured() -> None:
    """Ensure WhiteNoise middleware/storage and host parsing are configured."""
    values = _load_settings_with_env(
        {
            "DJANGO_ENV": "development",
            "DEBUG": "True",
            "ALLOWED_HOSTS": "example.com,api.example.com",
        }
    )

    assert values["ALLOWED_HOSTS"] == ["example.com", "api.example.com"]
    assert values["MIDDLEWARE"][0] == "django.middleware.security.SecurityMiddleware"
    assert values["MIDDLEWARE"][1] == "whitenoise.middleware.WhiteNoiseMiddleware"
    assert (
        values["STATICFILES_STORAGE"]
        == "whitenoise.storage.CompressedManifestStaticFilesStorage"
    )


def _load_settings_with_env(extra_env: dict[str, str]) -> dict[str, Any]:
    """Import investor_app.settings in a subprocess with controlled env vars."""
    env = os.environ.copy()
    for key in [
        "DJANGO_ENV",
        "DEBUG",
        "SECRET_KEY",
        "ALLOWED_HOSTS",
        "SECURE_SSL_REDIRECT",
        "SESSION_COOKIE_SECURE",
        "CSRF_COOKIE_SECURE",
        "SECURE_HSTS_SECONDS",
        "SECURE_HSTS_INCLUDE_SUBDOMAINS",
        "X_FRAME_OPTIONS",
    ]:
        env.pop(key, None)
    env.update(extra_env)

    script = """
import json
from investor_app import settings

print(json.dumps({
    "ALLOWED_HOSTS": settings.ALLOWED_HOSTS,
    "SECURE_SSL_REDIRECT": getattr(settings, "SECURE_SSL_REDIRECT", None),
    "SESSION_COOKIE_SECURE": getattr(settings, "SESSION_COOKIE_SECURE", None),
    "CSRF_COOKIE_SECURE": getattr(settings, "CSRF_COOKIE_SECURE", None),
    "SECURE_HSTS_SECONDS": getattr(settings, "SECURE_HSTS_SECONDS", None),
    "SECURE_HSTS_INCLUDE_SUBDOMAINS": getattr(settings, "SECURE_HSTS_INCLUDE_SUBDOMAINS", None),
    "X_FRAME_OPTIONS": settings.X_FRAME_OPTIONS,
    "MIDDLEWARE": settings.MIDDLEWARE,
    "STATICFILES_STORAGE": settings.STATICFILES_STORAGE,
}))
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=True,
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)

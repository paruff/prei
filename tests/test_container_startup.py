"""Regression tests for the published container startup contract.

This file validates that deployment configuration (Docker Compose, Render
blueprint) is structurally correct via YAML parsing, and that the entrypoint
script behaves correctly via stub execution.  The actual end-to-end container
smoke test lives in tests/test_docker_e2e.py — see there for build + run +
health-check.

Historical note: earlier versions of this file used raw substring matching
against Dockerfile / compose / render.yaml source text.  Those have been
replaced with proper YAML parsing and behavioral checks.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# Render blueprint — structural validation via YAML parsing
# ---------------------------------------------------------------------------


def test_render_blueprint_has_required_services() -> None:
    """Verify the Render blueprint declares required service and database."""
    blueprint = _load_yaml("render.yaml")

    services = {s["name"]: s for s in blueprint.get("services", [])}
    databases = {d["name"]: d for d in blueprint.get("databases", [])}

    assert "prei-web" in services, "prei-web service missing from render.yaml"
    assert "prei-db" in databases, "prei-db database missing from render.yaml"

    # Celery / Redis must not be present (MVP simplification)
    assert "prei-worker" not in services
    assert "prei-scheduler" not in services
    assert "prei-redis" not in services


def test_render_web_service_has_required_commands() -> None:
    """Verify the web service pre-deploy, start, and health-check commands."""
    blueprint = _load_yaml("render.yaml")
    svc = _service_by_name(blueprint, "prei-web")

    assert "collectstatic --noinput" in svc.get("buildCommand", "")
    assert "python manage.py migrate --noinput" in svc.get("preDeployCommand", "")
    assert "gunicorn investor_app.wsgi:application" in svc.get("startCommand", "")
    assert svc.get("healthCheckPath") == "/health/"


def test_render_web_service_has_required_env_vars() -> None:
    """Verify the web service declares all required environment variables."""
    blueprint = _load_yaml("render.yaml")
    svc = _service_by_name(blueprint, "prei-web")

    env_keys = {v["key"] for v in svc.get("envVars", [])}
    required = {
        "DJANGO_SETTINGS_MODULE",
        "DJANGO_ENV",
        "DEBUG",
        "SECRET_KEY",
        "ALLOWED_HOSTS",
        "DATABASE_URL",
    }
    missing = required - env_keys
    assert not missing, f"Missing env vars in render.yaml: {missing}"


def test_render_blueprint_excludes_celery_redis_config() -> None:
    """Verify no Celery broker or Redis config leaks into the blueprint."""
    raw = (REPO_ROOT / "render.yaml").read_text(encoding="utf-8")
    assert "REDIS_URL" not in raw
    assert "CELERY_BROKER_URL" not in raw
    assert "CELERY_RESULT_BACKEND" not in raw
    assert "celery" not in raw.lower()


# ---------------------------------------------------------------------------
# Docker Compose — structural validation via YAML parsing
# ---------------------------------------------------------------------------


def test_compose_healthcheck_allows_longer_prestart_migrations() -> None:
    """Verify Compose grants extra startup time before healthcheck failures."""
    compose = _load_yaml("docker-compose.yml")
    web = compose.get("services", {}).get("web", {})
    hc = web.get("healthcheck", {})

    assert hc.get("start_period") == "90s", (
        "healthcheck start_period should be 90s for migration time"
    )
    assert hc.get("retries") == 5, "healthcheck retries should be 5 for migration time"
    assert hc.get("interval") == "30s"
    assert hc.get("timeout") == "10s"


def test_compose_web_service_has_required_config() -> None:
    """Verify essential web-service configuration keys exist."""
    compose = _load_yaml("docker-compose.yml")
    web = compose.get("services", {}).get("web", {})

    assert web.get("image") == "ghcr.io/paruff/prei:latest"
    assert web.get("env_file") == ".env"
    assert "8000:8000" in web.get("ports", [])
    assert web.get("restart") == "unless-stopped"

    # Healthcheck test command must reference the health API endpoint
    hc_test = " ".join(web.get("healthcheck", {}).get("test", []))
    assert "/api/health/" in hc_test, "healthcheck test must call /api/health/"


def test_compose_runtime_env_vars_set() -> None:
    """Verify runtime environment overrides exist in the web service."""
    compose = _load_yaml("docker-compose.yml")
    env = compose.get("services", {}).get("web", {}).get("environment", {})

    # May be a dict or list of KEY=value strings
    env_str = str(env)
    assert "RUN_MIGRATIONS" in env_str
    assert "/app/.runtime" in env_str


# ---------------------------------------------------------------------------
# Entrypoint script — behavioral tests via stub Python
# ---------------------------------------------------------------------------


def test_entrypoint_skips_migrations_when_disabled(tmp_path: Path) -> None:
    """Verify RUN_MIGRATIONS=0 skips the migrate command before exec."""
    calls = _run_entrypoint_with_fake_python(tmp_path, run_migrations="0")
    assert calls == [
        "manage.py seed_data",
        "manage.py collectstatic --noinput",
        "-c print('ok')",
    ]


def test_entrypoint_runs_migrations_by_default(tmp_path: Path) -> None:
    """Verify migrations run before exec when RUN_MIGRATIONS is unset."""
    calls = _run_entrypoint_with_fake_python(tmp_path)
    assert calls == [
        "manage.py migrate --noinput",
        "manage.py seed_data",
        "manage.py collectstatic --noinput",
        "-c print('ok')",
    ]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_yaml(relative_path: str) -> dict[str, Any]:
    """Load and parse a YAML file from the repo root."""
    raw = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
    result = yaml.safe_load(raw)
    assert isinstance(result, dict)
    return result


def _service_by_name(blueprint: dict[str, Any], name: str) -> dict[str, Any]:
    """Return the Render service dict matching *name*, or raise."""
    services: list[dict[str, Any]] = blueprint.get("services", [])
    for svc in services:
        if svc.get("name") == name:
            return svc
    raise AssertionError(f"Service {name!r} not found in render blueprint")


def _run_entrypoint_with_fake_python(
    tmp_path: Path, run_migrations: str | None = None
) -> list[str]:
    """Run the entrypoint with a stub python binary and return intercepted calls."""
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    log_path = tmp_path / "calls.log"
    fake_python = fake_bin / "python"
    fake_python.write_text(
        "\n".join(
            [
                "#!/usr/bin/env python3",
                "import pathlib",
                "import sys",
                "pathlib.Path("
                f"{json.dumps(str(log_path))}"
                ').open("a", encoding="utf-8").write(" ".join(sys.argv[1:]) + "\\n")',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    fake_python.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    if run_migrations is None:
        env.pop("RUN_MIGRATIONS", None)
    else:
        env["RUN_MIGRATIONS"] = run_migrations

    subprocess.run(
        [
            "sh",
            str(REPO_ROOT / "scripts" / "entrypoint.sh"),
            "python",
            "-c",
            "print('ok')",
        ],
        check=True,
        cwd=REPO_ROOT,
        env=env,
    )

    return log_path.read_text(encoding="utf-8").splitlines()

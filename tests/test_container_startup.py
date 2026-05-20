"""Regression tests for the published container startup contract."""

import json
import os
from pathlib import Path
import re
import subprocess

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_GUARD_LINE = 'if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then'


def test_entrypoint_runs_migrations_before_execing_server() -> None:
    script = (REPO_ROOT / "scripts" / "entrypoint.sh").read_text(encoding="utf-8")

    migrate_line = "python manage.py migrate --noinput"
    exec_line = 'exec "$@"'

    assert MIGRATION_GUARD_LINE in script
    assert migrate_line in script
    assert exec_line in script
    assert (
        script.index(MIGRATION_GUARD_LINE)
        < script.index(migrate_line)
        < script.index(exec_line)
    )


def test_dockerfile_uses_entrypoint_and_writable_runtime_dirs() -> None:
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert re.search(r"^ENTRYPOINT\s+\[.*entrypoint\.sh.*\]$", dockerfile, re.MULTILINE)
    assert "mkdir -p /app/.runtime/matplotlib" in dockerfile
    assert "HOME=/app/.runtime" in dockerfile
    assert "MPLCONFIGDIR=/app/.runtime/matplotlib" in dockerfile
    assert "RUN_MIGRATIONS=1" in dockerfile
    assert "--start-period=90s" in dockerfile
    assert "--retries=5" in dockerfile


def test_compose_healthcheck_allows_longer_prestart_migrations() -> None:
    """Verify Compose grants extra startup time before healthcheck failures."""
    compose_file = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "start_period: 90s" in compose_file
    assert "retries: 5" in compose_file


def test_render_blueprint_has_required_services_and_web_commands() -> None:
    render_blueprint = yaml.safe_load(
        (REPO_ROOT / "render.yaml").read_text(encoding="utf-8")
    )
    services = render_blueprint["services"]
    databases = render_blueprint["databases"]
    service_by_name = {service["name"]: service for service in services}

    assert "prei-web" in service_by_name
    assert "prei-worker" in service_by_name
    assert "prei-scheduler" in service_by_name
    assert "prei-redis" in service_by_name
    assert any(database["name"] == "prei-db" for database in databases)

    web = service_by_name["prei-web"]
    worker = service_by_name["prei-worker"]
    scheduler = service_by_name["prei-scheduler"]

    assert "collectstatic --noinput" in web["buildCommand"]
    assert web["preDeployCommand"] == "python manage.py migrate --noinput"
    assert (
        web["startCommand"]
        == "daphne -b 0.0.0.0 -p $PORT investor_app.asgi:application"
    )
    assert web["healthCheckPath"] == "/health/"
    assert worker["startCommand"] == "celery -A investor_app worker -l info"
    assert scheduler["startCommand"] == "celery -A investor_app beat -l info"

    web_env_var_keys = {item["key"] for item in web["envVars"]}
    assert "DEBUG" in web_env_var_keys
    assert "ALLOWED_HOSTS" in web_env_var_keys
    assert "SECRET_KEY" in web_env_var_keys


def test_entrypoint_skips_migrations_when_disabled(tmp_path: Path) -> None:
    """Verify RUN_MIGRATIONS=0 skips the migrate command before exec."""
    calls = run_entrypoint_with_fake_python(tmp_path, run_migrations="0")

    assert calls == ["-c print('ok')"]


def test_entrypoint_runs_migrations_by_default(tmp_path: Path) -> None:
    """Verify migrations run before exec when RUN_MIGRATIONS is unset."""
    calls = run_entrypoint_with_fake_python(tmp_path)

    assert calls == ["manage.py migrate --noinput", "-c print('ok')"]


def run_entrypoint_with_fake_python(
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

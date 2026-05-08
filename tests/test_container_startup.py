"""Regression tests for the published container startup contract."""

import os
from pathlib import Path
import re
import subprocess

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_entrypoint_runs_migrations_before_execing_server() -> None:
    script = (REPO_ROOT / "scripts" / "entrypoint.sh").read_text(encoding="utf-8")

    guard_line = 'if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then'
    migrate_line = "python manage.py migrate --noinput"
    exec_line = 'exec "$@"'

    assert guard_line in script
    assert migrate_line in script
    assert exec_line in script
    assert (
        script.index(guard_line) < script.index(migrate_line) < script.index(exec_line)
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
    compose_file = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "start_period: 90s" in compose_file
    assert "retries: 5" in compose_file


def test_entrypoint_skips_migrations_when_disabled(tmp_path: Path) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    log_path = tmp_path / "calls.log"
    fake_python = fake_bin / "python"
    fake_python.write_text(
        "\n".join(
            [
                "#!/usr/bin/env sh",
                f'printf "%s\\n" "$*" >> "{log_path}"',
                'if [ "$1" = "-c" ]; then',
                "  shift",
                '  exec python3 -c "$@"',
                "fi",
                "exit 0",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    fake_python.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["RUN_MIGRATIONS"] = "0"

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

    calls = log_path.read_text(encoding="utf-8").splitlines()
    assert calls == ["-c print('ok')"]

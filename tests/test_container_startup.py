"""Regression tests for the published container startup contract."""

from pathlib import Path
import re

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_entrypoint_runs_migrations_before_execing_server() -> None:
    script = (REPO_ROOT / "scripts" / "entrypoint.sh").read_text(encoding="utf-8")

    migrate_line = "python manage.py migrate --noinput"
    exec_line = 'exec "$@"'

    assert migrate_line in script
    assert exec_line in script
    assert script.index(migrate_line) < script.index(exec_line)


def test_dockerfile_uses_entrypoint_and_writable_runtime_dirs() -> None:
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert re.search(r"^ENTRYPOINT\s+\[.*entrypoint\.sh.*\]$", dockerfile, re.MULTILINE)
    assert "mkdir -p /app/.runtime/matplotlib" in dockerfile
    assert "HOME=/app/.runtime" in dockerfile
    assert "MPLCONFIGDIR=/app/.runtime/matplotlib" in dockerfile

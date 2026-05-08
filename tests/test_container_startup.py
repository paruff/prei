"""Regression tests for the published container startup contract."""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_entrypoint_runs_migrations_before_execing_server() -> None:
    script = (REPO_ROOT / "scripts" / "entrypoint.sh").read_text(encoding="utf-8")

    assert "python manage.py migrate --noinput" in script
    assert 'exec "$@"' in script


def test_dockerfile_uses_entrypoint_and_writable_runtime_dirs() -> None:
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert 'ENTRYPOINT ["sh", "./scripts/entrypoint.sh"]' in dockerfile
    assert "HOME=/tmp" in dockerfile
    assert "MPLCONFIGDIR=/tmp/matplotlib" in dockerfile

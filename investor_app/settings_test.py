from .settings import *  # noqa
from pathlib import Path

# Force SQLite for tests to avoid external DB dependency
BASE_DIR = Path(__file__).resolve().parent.parent
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(BASE_DIR / "test_db.sqlite3"),
        # SQLite defaults the pytest-django test database to :memory: unless
        # TEST["NAME"] is set explicitly. In-memory SQLite connections are
        # private per-connection, so the live_server fixture's background
        # thread (a separate connection) sees an empty, unmigrated schema
        # while the main test thread sees the real one. A file-based test
        # database is required for live_server to work with SQLite — see
        # https://pytest-django.readthedocs.io/en/latest/database.html#live-server
        "TEST": {
            "NAME": str(BASE_DIR / "test_db.sqlite3"),
        },
    }
}

# Keep pytest/CI HTTP test-client behavior stable even when DEBUG=False is set
# in workflow environments.
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Clear proxy header — tests don't run behind a TLS-terminating proxy, and
# setting this can cause false positives when the test client doesn't send
# HTTP_X_FORWARDED_PROTO.
SECURE_PROXY_SSL_HEADER = None  # type: ignore[assignment]

from .settings import *  # noqa
from pathlib import Path

# Force SQLite for tests to avoid external DB dependency
BASE_DIR = Path(__file__).resolve().parent.parent
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(BASE_DIR / "test_db.sqlite3"),
    }
}

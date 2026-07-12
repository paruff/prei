from __future__ import annotations

import os
from pathlib import Path
from decimal import Decimal

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, True),
)

env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(str(env_file))

DJANGO_ENV = env("DJANGO_ENV", default="development").lower()
IS_PRODUCTION = DJANGO_ENV == "production"

DEBUG = (
    env.bool("DEBUG", default=False)
    if IS_PRODUCTION
    else env.bool("DEBUG", default=True)
)
SECRET_KEY = (
    env("SECRET_KEY")
    if IS_PRODUCTION
    else env.str("SECRET_KEY", default="dev-only-secret-key-not-for-production")
)
ALLOWED_HOSTS = [
    host
    for host in map(
        str.strip, env("ALLOWED_HOSTS", default="localhost,127.0.0.1").split(",")
    )
    if host
]

# ---------------------------------------------------------------------------
# CSRF Trusted Origins & Proxy Headers
# ---------------------------------------------------------------------------
# Django 4+ requires CSRF_TRUSTED_ORIGINS when serving over HTTPS through a
# TLS-terminating proxy (Codespaces, Render, Fly.io, etc.). Without this,
# secure requests get: "Origin checking failed — {origin} does not match
# any trusted origins."
#
# Build the list from four sources:
#   1. The CSRF_TRUSTED_ORIGINS env var (comma-separated, for explicit config)
#   2. GitHub Codespace preview URL (auto-detected from env)
#   3. ALLOWED_HOSTS entries with https:// prefix
#   4. Sensible local-dev fallbacks (localhost, 127.0.0.1)
# ---------------------------------------------------------------------------
CSRF_TRUSTED_ORIGINS = list(
    map(str.strip, env("CSRF_TRUSTED_ORIGINS", default="").split(","))
)
CSRF_TRUSTED_ORIGINS = [o for o in CSRF_TRUSTED_ORIGINS if o]

# Auto-detect GitHub Codespace URL for port-forwarding.
# Pattern: https://{CODESPACE_NAME}-{PORT}.{GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN}
codespace_name = os.environ.get("CODESPACE_NAME")
codespace_domain = os.environ.get("GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN")
if codespace_name and codespace_domain:
    CSRF_TRUSTED_ORIGINS.append(f"https://{codespace_name}-8000.{codespace_domain}")

# Add https:// variants of all ALLOWED_HOSTS for behind-proxy scenarios
CSRF_TRUSTED_ORIGINS.extend(
    f"https://{host}" for host in ALLOWED_HOSTS if host not in ("*",)
)

# Always trust local origins for dev (both HTTP and HTTPS variants for
# browsers that auto-upgrade via HSTS or localStorage HTTPS redirects)
for origin in (
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "https://localhost:8000",
    "https://127.0.0.1:8000",
):
    if origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(origin)

# Signal that Django is behind a TLS-terminating proxy (Codespaces, Render,
# Fly.io, load balancers). This tells Django to trust the X-Forwarded-Proto
# header so that request.is_secure() returns True and redirects use https://.
# Removed in settings_test.py to keep test behaviour predictable.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

if not DEBUG:
    SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
    SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=True)
    CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=True)
    SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31536000)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool(
        "SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True
    )
    SECURE_HSTS_PRELOAD = env.bool("SECURE_HSTS_PRELOAD", default=True)
    SECURE_CONTENT_TYPE_NOSNIFF = env.bool("SECURE_CONTENT_TYPE_NOSNIFF", default=True)

X_FRAME_OPTIONS = "DENY"

# Session security — sessions expire on browser close and have a maximum age.
# 1209600 seconds = 14 days.  The DB-backed session engine (default) persists
# sessions beyond browser close — SESSION_EXPIRE_AT_BROWSER_CLOSE forces a fresh
# login each time the browser restarts, while SESSION_COOKIE_AGE sets the hard
# upper limit regardless of browser state.
SESSION_COOKIE_AGE = 1209600  # 14 days
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = True

# CORS is intentionally NOT configured.  This project serves a server-rendered
# Django template frontend (no SPA / separate-client architecture).  All API
# calls are same-origin (same domain, same port).  CORS headers are only needed
# when a separate frontend domain makes cross-origin requests, which is not
# a current or planned architecture.  If a mobile app, SPA, or third-party API
# consumer is added, add django-cors-headers to requirements.txt and configure
# CORS_ALLOWED_ORIGINS at that time.

DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
    )
}

# Enable SQLite WAL mode + busy timeout for concurrent reads/writes.
# Prevents "database is locked" errors from background threads (e.g. VRM scrape).
if DATABASES["default"]["ENGINE"] == "django.db.backends.sqlite3":
    opts = DATABASES["default"].setdefault("OPTIONS", {})
    opts.setdefault("init_command", (
        "PRAGMA journal_mode=WAL;"
        "PRAGMA busy_timeout=5000;"
        "PRAGMA synchronous=NORMAL;"
    ))
    # Also set a timeout so Django waits instead of failing immediately
    DATABASES["default"].setdefault("timeout", 20)

LOGIN_REDIRECT_URL = "/dashboard/"
LOGOUT_REDIRECT_URL = "/accounts/login/"

TIME_ZONE = env("TIME_ZONE", default="UTC")
USE_TZ = True

LANGUAGE_CODE = "en-us"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "rest_framework",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "investor_app.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.version",
            ],
        },
    },
]

WSGI_APPLICATION = "investor_app.wsgi.application"

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Financial defaults (do not hardcode in code; override via env)
FINANCE_DEFAULTS = {
    "vacancy_rate": Decimal(env("VACANCY_RATE", default="0.05")),
    "management_fee_rate": Decimal(env("MANAGEMENT_FEE_RATE", default="0.08")),
    "capex_reserve_rate": Decimal(env("CAPEX_RESERVE_RATE", default="0.05")),
    "down_payment_rate": Decimal(env("DOWN_PAYMENT_RATE", default="0.20")),
    "loan_interest_rate_pct": Decimal(env("LOAN_INTEREST_RATE_PCT", default="7.5")),
    "loan_term_years": int(env("LOAN_TERM_YEARS", default="30")),
    # Minimum DSCR required by most lenders for investment-property refinancing.
    # Fannie Mae / conventional lenders typically require >= 1.25; some require 1.15–1.30.
    "brrrr_dscr_threshold": Decimal(env("BRRRR_DSCR_THRESHOLD", default="1.25")),
}

LOG_LEVEL = env("LOG_LEVEL", default="INFO")

# Structured logging for analytics pipelines and services.
# Use verbose formatter (includes pathname + lineno) in DEBUG mode; simple otherwise.
_log_formatter = "verbose" if DEBUG else "simple"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(levelname)s %(name)s %(pathname)s:%(lineno)d %(message)s",
        },
        "simple": {
            "format": "%(levelname)s %(name)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": _log_formatter,
        }
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
    "loggers": {
        "investor_app": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": True,
        },
        "core": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": True,
        },
    },
}

# Django REST Framework settings
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.AnonRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "user": "1000/day",
        "anon": "100/day",
    },
}

# Password validation — Django defaults
# See https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": 8,
        },
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Growth areas API cache duration (in seconds)
GROWTH_AREAS_CACHE_DURATION = 86400  # 24 hours

# BRRRR rehab cost per square foot by renovation level.
# These are national averages and approximations only — actual costs vary
# significantly by market, contractor, and property condition.
# Override individual values via env vars: REHAB_COST_COSMETIC,
# REHAB_COST_MODERATE, REHAB_COST_FULL_GUT (dollar amounts, e.g. "15").
# FRED API key for economic data (employment growth, unemployment)
FRED_API_KEY: str = env("FRED_API_KEY", default="")
HUD_API_KEY: str = env("HUD_API_KEY", default="")

REHAB_COST_PER_SQFT: dict[str, Decimal] = {
    "cosmetic": Decimal(
        env("REHAB_COST_COSMETIC", default="15")
    ),  # paint, carpet, fixtures
    "moderate": Decimal(
        env("REHAB_COST_MODERATE", default="35")
    ),  # kitchen, baths, flooring
    "full_gut": Decimal(
        env("REHAB_COST_FULL_GUT", default="75")
    ),  # structural, mechanicals, full reno
}

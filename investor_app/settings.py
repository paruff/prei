from __future__ import annotations

from pathlib import Path
from decimal import Decimal

import environ
from django.core.exceptions import ImproperlyConfigured
from django.core.management.utils import get_random_secret_key

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
    else env("SECRET_KEY", default=get_random_secret_key())
)
ALLOWED_HOSTS = (
    env.list("ALLOWED_HOSTS")
    if IS_PRODUCTION
    else env.list("ALLOWED_HOSTS", default=["*"])
)

if IS_PRODUCTION:
    if not env("ALLOWED_HOSTS", default="").strip():
        raise ImproperlyConfigured(
            "ALLOWED_HOSTS must be set when DJANGO_ENV=production."
        )
    SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
    SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=True)
    CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=True)
    SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31536000)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool(
        "SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True
    )
    SECURE_HSTS_PRELOAD = env.bool("SECURE_HSTS_PRELOAD", default=True)
    SECURE_CONTENT_TYPE_NOSNIFF = env.bool("SECURE_CONTENT_TYPE_NOSNIFF", default=True)
    X_FRAME_OPTIONS = env("X_FRAME_OPTIONS", default="DENY")

DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
    )
}

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
    "rest_framework",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
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
            ],
        },
    },
]

WSGI_APPLICATION = "investor_app.wsgi.application"

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

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
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.AnonRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "user": "1000/day",
        "anon": "100/day",
    },
}

# Growth areas API cache duration (in seconds)
GROWTH_AREAS_CACHE_DURATION = 86400  # 24 hours

# BRRRR rehab cost per square foot by renovation level.
# These are national averages and approximations only — actual costs vary
# significantly by market, contractor, and property condition.
# Override individual values via env vars: REHAB_COST_COSMETIC,
# REHAB_COST_MODERATE, REHAB_COST_FULL_GUT (dollar amounts, e.g. "15").
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

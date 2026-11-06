# investor_app

## Overview
Django project package: settings, URL root, ASGI/WSGI entry points, and the `finance/` pure-math library.

## Interface
- `settings.py`: env-driven config via `django-environ` (`DJANGO_ENV`, `SECRET_KEY`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `DATABASES`, `CACHES`, `REST_FRAMEWORK`, CSP policy, `LOGGING`, optional OTLP export). `FINANCE_DEFAULTS` (Decimal rates: vacancy, management fee, capex, down payment, interest, term, tax, insurance, maintenance, BRRRR DSCR). API keys: `FRED_API_KEY`, `HUD_API_KEY`, `HUD_FMR_TOKEN`, `ATTOM_API_KEY`, `RENTO_METER_API_KEY`; rehab cost per sq ft settings.
- `settings_test.py`: test settings.
- `urls.py`: `admin/`, `accounts/` (django auth), `api/` (`core.api_urls`), root (`core.urls`).
- `asgi.py`, `wsgi.py`: server entry points.
- [./finance/README.md](./finance/README.md): finance math.

## Invariants
- `ROOT_URLCONF = "investor_app.urls"`; `WSGI_APPLICATION = "investor_app.wsgi.application"`.
- Session cookies HttpOnly, 14-day age, expire on browser close; `X_FRAME_OPTIONS = "DENY"`.
- Production (`IS_PRODUCTION`) enforces secure settings and raises `ImproperlyConfigured` on missing required config.

## Side Effects
- Reads a `.env` file and the process environment at import; configures logging and optional OpenTelemetry.

## Verification
- Run: `.venv/bin/python -m pytest <paths>` (configured by `pytest.ini`)

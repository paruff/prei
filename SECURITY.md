# Security Policy — prei

> **prei** is a Django 4.2 LTS application for passive residential real estate investment analytics.
> Stack: Python 3.11 · Django · PostgreSQL · DRF · Celery · Redis · numpy-financial
>
> This document covers responsible disclosure, stack-specific rules enforced in code review,
> the current security posture, known gaps that require remediation, and the developer
> security checklist applied to every PR.

---

## 1. Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Report vulnerabilities privately via **GitHub Security Advisories**:

1. Go to the [Security tab](https://github.com/paruff/prei/security) of this repository.
2. Click **"Report a vulnerability"**.
3. Provide: affected component, reproduction steps, potential impact, and any suggested fix.

**Response SLA:**

| Severity | Initial acknowledgement | Target remediation |
|---|---|---|
| Critical | 24 hours | 3 business days |
| High | 48 hours | 7 business days |
| Medium / Low | 5 business days | Next release cycle |

Reporters who follow responsible disclosure will be credited in the release notes (unless they prefer anonymity).

---

## 2. Supported Versions

| Version / Branch | Supported |
|---|---|
| `main` | ✅ Active |
| Feature branches | ⚠️ Not independently supported — merge to `main` |

---

## 3. Stack-Specific Security Rules

These rules are enforced in code review and by `@security-agent`. Every PR that touches the listed areas must satisfy all applicable rules before merge.

### 3.1 Authentication and Authorization

- **Rule AUTH-01:** Every DRF view that reads or writes user-scoped data (e.g., `Property`, `InvestmentAnalysis`, `UserWatchlist`, `AuctionAlert`, `NotificationPreference`) **must** set `permission_classes = [IsAuthenticated]` or use the global DRF default (see §4.1). Views that deliberately serve public data must be explicitly annotated with a comment explaining why unauthenticated access is acceptable.
- **Rule AUTH-02:** Every queryset over user-owned models **must** be filtered by `request.user`. A queryset `MyModel.objects.all()` on a user-scoped model is a **CRITICAL** finding.
- **Rule AUTH-03:** `request.user` must not be trusted from request body data. Always derive the user from `request.user` (set by authentication middleware), never from a field in the payload.

### 3.2 Secrets and Credentials

- **Rule SEC-01:** No API keys, `SECRET_KEY`, database credentials, or tokens hardcoded in any file committed to the repository — including default fallback values in `settings.py`. Use `env("VAR")` without a fallback (this raises `ImproperlyConfigured` if missing, which is the desired behaviour in production).
- **Rule SEC-02:** `.env` must never be committed. `.gitignore` enforces this; verify before every commit.
- **Rule SEC-03:** New integrations that require credentials must source them from environment variables only. Document required variables in `.env.example` (with placeholder values).

### 3.3 Input Validation

- **Rule VAL-01:** All numeric inputs in DRF serializers must declare `min_value` (and `max_value` where sensible). See `core/serializers.py` for the established pattern.
- **Rule VAL-02:** All free-form string inputs must have `max_length` declared. Long strings without a length limit are a Denial-of-Service vector.
- **Rule VAL-03:** Financial division operations must guard against zero denominators. Return `Decimal("0")` or raise `ValueError` with a clear message. Never let `ZeroDivisionError` propagate to the HTTP response layer.
- **Rule VAL-04:** Any parameter used to construct a DB filter (state code, location, property type) must pass through a named validator function in `core/validators.py`. Inline validation in views is not permitted.

### 3.4 Financial Calculations

- **Rule FIN-01:** Use `Decimal` for all currency values stored in the database and returned in API responses. Convert to `float` only as an intermediate value for `numpy`/`numpy-financial` calls, and convert back to `Decimal` before returning.
- **Rule FIN-02:** `numpy-financial` calls (`npf.irr`, `npf.npv`, etc.) must be wrapped in `try/except Exception` with a safe fallback (return `Decimal("0")`) and a `logger.warning` call so silent NaN/Inf results are not silently returned to clients.
- **Rule FIN-03:** Financial logic lives exclusively in `investor_app/finance/utils.py`. Putting calculations in views, models, or templates is an architecture violation and a testability/auditability risk.

### 3.5 External API Calls and Web Scraping

- **Rule INT-01:** External API calls (ATTOM, HUD) must be made exclusively from `core/integrations/`. Views may not call external services directly.
- **Rule INT-02:** URLs used in HTTP requests from integration adapters must be constructed from hardcoded base URLs + validated path components. Never interpolate user-supplied data directly into a URL to avoid SSRF.
- **Rule INT-03:** The HUD scraper (`core/integrations/sources/hud_scraper.py`) targets a fixed, hardcoded `BASE_URL`. Any change to make the target URL dynamic or user-configurable requires explicit security review.
- **Rule INT-04:** API responses from external services must be parsed defensively. Never pass raw external API error messages to client responses — log them server-side and return a generic error string.

### 3.6 Error Handling and Information Leakage

- **Rule ERR-01:** Raw database error messages, stack traces, and internal identifiers must never reach API responses in production. The pattern used throughout `core/api_views.py` (catching `DatabaseError`, logging the detail, returning a generic message) is the required approach.
- **Rule ERR-02:** `DEBUG = True` must never be set in any production deployment. Enabling `DEBUG` exposes the full stack trace, local variables, settings values, and SQL queries in error responses.
- **Rule ERR-03:** Logging of user-supplied query parameters (e.g., `state`, `location`) is acceptable for operational visibility but must not log credentials, tokens, or financial amounts.

### 3.7 Dependency Management

- **Rule DEP-01:** New Python dependencies require PM + human developer sign-off before being added to `requirements.txt`. AI agents must not add dependencies unilaterally.
- **Rule DEP-02:** Dependabot is configured for both `pip` and `docker` on a weekly schedule. Dependabot PRs for security updates must be reviewed and merged within the SLA in §1.
- **Rule DEP-03:** `playwright` is listed in `requirements.txt` for scraper support. It must not be used to fetch user-supplied URLs (SSRF risk). Review any Playwright usage that accepts external input.

---

## 4. Current Security Posture

### 4.1 What Is in Place

| Control | Status | Notes |
|---|---|---|
| Django `SecurityMiddleware` | ✅ Active | Included in `MIDDLEWARE` |
| CSRF protection | ✅ Active | `CsrfViewMiddleware` in `MIDDLEWARE` |
| Clickjacking protection | ✅ Active | `XFrameOptionsMiddleware` (default: `SAMEORIGIN`) |
| Rate throttling | ✅ Active | `UserRateThrottle` + `AnonRateThrottle` at 100/hour each |
| Input validation — serializers | ✅ Active | `min_value`, `max_value`, `max_length` on numeric fields |
| Input validation — query params | ✅ Active | `core/validators.py` functions used in all views |
| Error message sanitisation | ✅ Active | Generic error strings returned; raw DB errors logged only |
| Non-root Docker user | ✅ Active | `adduser --system app; USER app` in `Dockerfile` |
| Dependency scanning | ✅ Active | Dependabot weekly for pip + docker |
| Secrets via env vars | ✅ Active | `django-environ` used throughout `settings.py` |
| Division-by-zero guards | ✅ Active | All finance utils guard denominators |
| `numpy-financial` safe fallback | ✅ Active | `irr()` wraps in `try/except`, returns `Decimal("0")` |

### 4.2 Known Gaps — Remediation Required

The following items are **not yet in place** and represent real risk in a production deployment. Each is flagged with a severity level using the scale: CRITICAL → HIGH → MEDIUM → LOW.

---

#### 🔴 CRITICAL — GAP-01: DRF default permission class is `AllowAny`

**Location:** `investor_app/settings.py`, `REST_FRAMEWORK` block.

**Risk:** `DEFAULT_PERMISSION_CLASSES` is not set. The DRF default is `AllowAny`, meaning every API endpoint is publicly accessible without authentication unless the view individually sets `permission_classes = [IsAuthenticated]`. A missed annotation on a single view exposes user data.

**Required fix:**

```python
# investor_app/settings.py — REST_FRAMEWORK block
"DEFAULT_AUTHENTICATION_CLASSES": [
    "rest_framework.authentication.SessionAuthentication",
    # Add TokenAuthentication or JWTAuthentication here when API clients are added
],
"DEFAULT_PERMISSION_CLASSES": [
    "rest_framework.permissions.IsAuthenticated",
],
```

Views serving public data (e.g., growth areas, foreclosure listings) must then explicitly declare:

```python
permission_classes = [AllowAny]  # Public endpoint — no user data returned
```

This makes the security model explicit and opt-out rather than accidentally opt-in.

---

#### 🔴 CRITICAL — GAP-02: `DEBUG` defaults to `True`

**Location:** `investor_app/settings.py` line 10.

```python
env = environ.Env(
    DEBUG=(bool, True),  # ← defaults to True if env var absent
)
```

**Risk:** If `DEBUG` is not set in the production environment (easy to miss during deploy), Django serves full stack traces, local variable dumps, SQL query logs, and settings values in all HTTP error responses.

**Required fix:** Remove the default. Force an explicit value to be set:

```python
env = environ.Env(
    DEBUG=(bool, False),  # Safe default — must explicitly opt in to debug mode
)
```

---

#### 🔴 CRITICAL — GAP-03: `SECRET_KEY` has an insecure fallback value

**Location:** `investor_app/settings.py` line 19.

```python
SECRET_KEY = env("SECRET_KEY", default="dev-secret-key-change-me")
```

**Risk:** If `SECRET_KEY` is not set in the production environment, Django silently uses the hardcoded string. This makes session tokens, CSRF tokens, and signed cookies forgeable by anyone who knows (or guesses) the default string.

**Required fix:** Remove the `default` argument entirely:

```python
SECRET_KEY = env("SECRET_KEY")  # Raises ImproperlyConfigured if not set
```

---

#### 🔴 CRITICAL — GAP-04: `ALLOWED_HOSTS` defaults to `["*"]`

**Location:** `investor_app/settings.py` line 20.

```python
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["*"])
```

**Risk:** Allows any `Host:` header value, enabling Host Header Injection attacks (cache poisoning, password reset link hijacking).

**Required fix:** Set a safe default that forces an explicit host list to be configured:

```python
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")  # Raises ImproperlyConfigured if not set
```

And in production, set `ALLOWED_HOSTS=yourdomain.com` in the environment.

---

#### 🟠 HIGH — GAP-05: HTTPS/HSTS not configured

**Location:** `investor_app/settings.py` — no `SECURE_*` settings present.

**Risk:** Without HTTPS enforcement, session cookies and API keys transit unencrypted. Without HSTS, a user who visits the HTTP version is vulnerable to SSL stripping.

**Required fix (production settings or environment-conditional block):**

```python
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True  # legacy header — still useful
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
```

Note: If the app sits behind a TLS-terminating proxy (e.g., Render, Fly.io), set `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")` instead of `SECURE_SSL_REDIRECT`.

---

#### 🟠 HIGH — GAP-06: Redis has no authentication in `docker-compose.yml`

**Location:** `docker-compose.yml` — no Redis service with password; `REDIS_URL` defaults to `redis://redis:6379/0` (no auth).

**Risk:** If the Redis port is accidentally exposed (e.g., misconfigured cloud security group), an attacker can read all cached financial data, session data, and Celery task queues without credentials.

**Required fix:**

1. Add a Redis password to `docker-compose.yml`:
   ```yaml
   redis:
     image: redis:7-alpine
     command: redis-server --requirepass ${REDIS_PASSWORD}
   ```
2. Add `REDIS_PASSWORD` to `.env.example`.
3. Update `REDIS_URL`, `CELERY_BROKER_URL`, and `CELERY_RESULT_BACKEND` to include the password:
   ```
   REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
   ```

---

#### 🟡 MEDIUM — GAP-07: No Content Security Policy (CSP) header

**Risk:** Without CSP, any XSS payload injected into a template can execute arbitrary scripts, load external resources, or exfiltrate data.

**Required fix:** Add `django-csp` to `requirements.txt` (requires PM approval) and configure a restrictive policy for templates that render user data. Alternatively, add a CSP header in the reverse proxy configuration (Nginx/Caddy).

---

#### 🟡 MEDIUM — GAP-08: No CORS configuration

**Risk:** If a browser-based frontend SPA is added (likely given the DRF API surface), without `django-cors-headers`, cross-origin requests from the frontend will fail. Conversely, a wildcard CORS policy (common workaround) would allow any origin to make credentialed requests.

**Required fix:** When a frontend is added, install `django-cors-headers` and set `CORS_ALLOWED_ORIGINS` to an explicit list. Never use `CORS_ALLOW_ALL_ORIGINS = True` in production.

---

#### 🟡 MEDIUM — GAP-09: `PostgreSQL` container has no explicit password in `docker-compose.yml`

**Location:** `docker-compose.yml` uses a minimal `postgres:16-alpine` image without specifying a password environment variable. The default PostgreSQL image uses `POSTGRES_PASSWORD=postgres` (from `.env.example`).

**Risk:** Trivially guessable database password if the Postgres port is exposed.

**Required fix:** Use a strong, randomly-generated password. Rotate `.env.example` to document `POSTGRES_PASSWORD=<strong-random-password>` and enforce it in `docker-compose.yml` via `environment: POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}`.

---

#### 🟡 MEDIUM — GAP-10: Anonymous throttle rate (100/hour) may be too permissive for financial endpoints

**Location:** `investor_app/settings.py` `DEFAULT_THROTTLE_RATES.anon: "100/hour"`.

**Risk:** The `/api/carrying-costs/` and `/api/strategy-comparison/` endpoints perform CPU-bound financial calculations. At 100 unauthenticated requests per hour, a modest botnet can cause meaningful compute load.

**Required fix:** Apply a stricter throttle to write/calculation endpoints. Create a `CalculationRateThrottle` class (e.g., `20/hour` for anon) and apply it specifically to `calculate_carrying_costs` and `compare_strategies`.

---

#### 🟢 LOW — GAP-11: `Dockerfile` references Python 3.14 (pre-release)

**Location:** `Dockerfile` line 4: `ARG PYTHON_VERSION=3.14`.

**Risk:** Python 3.14 is not yet released as stable (as of the time of writing). Using a pre-release Python version in production containers can introduce undiscovered security vulnerabilities and unpredictable behavior.

**Required fix:** Pin to `python:3.11-slim`, which aligns with the project's stated Python 3.11 requirement.

---

#### 🟢 LOW — GAP-12: CI workflow has `permissions: contents: write`

**Location:** `.github/workflows/ci.yml` line 12.

**Risk:** `contents: write` allows the workflow to push commits back to the repository. This is intentional (ruff auto-fix commits), but it means a compromised workflow step (e.g., via a malicious dependency) could push arbitrary code to the branch.

**Mitigation:** Scope the permission to the minimum required step. Consider moving the auto-commit step to a separate workflow with a short-lived token, or restricting the permission to only the auto-commit step using step-level permissions (GitHub Actions `permissions` at job/step level).

---

## 5. Developer Security Checklist

Apply this checklist to every PR that touches the areas listed. It supplements the main PR template.

### On every PR

- [ ] No secrets, API keys, or credentials in any committed file (including test fixtures)
- [ ] `DEBUG` is not hardcoded to `True` anywhere
- [ ] No new `default=` fallback for `SECRET_KEY` or `ALLOWED_HOSTS`

### On PRs touching `core/api_views.py` or `core/serializers.py`

- [ ] Every view that accesses user-owned data has `permission_classes = [IsAuthenticated]`
- [ ] Every queryset over a user-scoped model is filtered by `request.user`
- [ ] No raw DB error messages or stack traces in response bodies
- [ ] All user-supplied parameters pass through a validator before being used in a query
- [ ] String inputs have `max_length` declared in the serializer

### On PRs touching `investor_app/finance/utils.py` or `core/services/`

- [ ] All division operations guard against zero denominators
- [ ] `numpy-financial` calls are wrapped in `try/except` with a safe `Decimal("0")` fallback
- [ ] No `float` used for values that will be stored in the database
- [ ] Boundary tests exist: negative, zero, and very large input values

### On PRs touching `core/integrations/`

- [ ] No user-supplied input interpolated into external URLs (SSRF prevention)
- [ ] Raw external API error messages not forwarded to client responses
- [ ] New API keys sourced from environment variables only, documented in `.env.example`

### On PRs touching `requirements.txt`

- [ ] Dependency addition approved by PM + human developer
- [ ] Dependency checked against GitHub Advisory Database (or `pip audit`)
- [ ] No transitive dependency introduces a known CVE

---

## 6. Secrets Management

| Secret | Where it lives | Rotation procedure |
|---|---|---|
| `SECRET_KEY` | Environment variable | Generate with `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`. Rotate by updating env var and redeploying. All existing sessions are invalidated. |
| `DATABASE_URL` | Environment variable | Update password in Postgres, update `DATABASE_URL`, redeploy. |
| `ATTOM_API_KEY` | Environment variable | Rotate via ATTOM developer portal. Update env var. |
| `REDIS_URL` | Environment variable | Update Redis `requirepass`, update `REDIS_URL`. |
| `CELERY_BROKER_URL` | Environment variable | Same as `REDIS_URL`. |

**Never commit `.env`.** The `.gitignore` prevents this but always verify before pushing.

---

## 7. Vulnerability Disclosure History

| Date | Severity | Component | Status |
|---|---|---|---|
| — | — | — | No public disclosures to date |

---

## 8. Policy Review

This document is reviewed:

- Quarterly (scheduled)
- After any security incident
- When a new integration or authentication mechanism is added

**Last reviewed:** 2026-05-06
**Next scheduled review:** 2026-08-06
**Owner:** PM / Tech Lead (see `docs/AI_POLICY.md` for accountability structure)

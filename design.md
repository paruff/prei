# Design: Data Layer & Infrastructure Upgrades for Beta Readiness

**Feature**: Core product upgrades — rent data, GACS validation, crime data, Postgres, Celery, multi-user
**Spec**: `specification.md`
**Status**: Draft

---

## Architecture Overview

Five parallel workstreams:

```
┌─────────────────────────────────────────────────────────────────┐
│                        Rent Data Pipeline                       │
│  VRM (existing) → Rentcast (new) → ATTOM (probe) → HUD FMR      │
│  Screening fallback chain: rent_estimate =                      │
│    prop.rent || rentcast(zip) || attom(prop) || hud_fmr(zip)    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      GACS Validation Engine                     │
│  Backtest: GACS_t vs FHFA_12mo_appreciation_t+12               │
│  Weight grid search → publish sensitivity → lock weights        │
│  Signal completion: schools, supply constraint, employment fix  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Crime Data Adapter                        │
│  Retry FBI CDE → if fail: SpotCrime → CityProtect → local PD   │
│  Interface: get_crime_score(zip) → (score, confidence, source)  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Infrastructure Foundation                     │
│  Postgres (docker-compose) → Celery + Redis → Team model        │
│  Async: screening, discovery, VRM scrape                        │
│  Sharing: PipelineProperty.team (FK) + TeamMembership          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Security Hardening                          │
│  django-csp → CSP, Permissions-Policy, CORP headers            │
│  SRI on external scripts → ZAP WARN → 0                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Design

### 1. Rentcast Adapter (`core/integrations/sources/rentcast_adapter.py`)

```python
class RentcastAdapter:
    """Rentcast.io API — rent estimates by address/ZIP."""

    def get_rent_estimate(self, address: str = None, zip_code: str = None) -> RentEstimate:
        """
        Returns RentEstimate(monthly_rent: Decimal, confidence: float, source: str)
        Confidence: 0.7–0.95 based on data density.
        """

    def get_rent_comps(self, address: str, radius_km: float = 1.0) -> list[RentComp]:
        """Nearby rent comps for manual review."""
```

**Integration point**: `core/services/screening.py:_get_rent_estimate()` — new fallback chain.

**Spike first**: API key, rate limits, coverage for TX/FL/TN.

---

### 2. ATTOM Rent Probe (`core/integrations/sources/attom_adapter.py`)

Extend existing ATTOM adapter:
```python
def get_rent_estimate(self, address: str) -> RentEstimate | None:
    """Check if ATTOM Property API returns rental_estimate field."""
```

If available, insert between VRM and Rentcast in fallback chain.

---

### 3. GACS Backtest & Validation (`core/services/market_scoring.py` + scripts)

**Backtest script** (`scripts/backtest_gacs.py`):
```python
def backtest_gacs():
    # 1. Load historical GrowthArea records (GACS_t, components)
    # 2. Load FHFA HPI or Zillow ZHVI for same cities, 12mo forward
    # 3. Regress GACS_t → appreciation_t+12
    # 4. Grid search weights (employment 20-40%, pop 10-20%, income 10-20%, etc.)
    # 5. Output: best weights, R², sensitivity table, confidence bands
```

**Signal completion**:
- **Schools**: `core/integrations/market/schools.py` → GreatSchools API (needs key)
- **Supply constraint**: `core/integrations/market/supply.py` → Census building permits / HUD permit data
- **Employment**: Fix fallback to prefer county QCEW, only state FRED when county missing

**Output**: Updated `GrowthArea` model with validated weights + confidence bands per signal.

---

### 4. Crime Data Adapter (`core/integrations/market/crime.py`)

**Retry FBI CDE**:
```python
# Correct endpoint: api.usa.gov/crime/fbi/cde/summary/agencies
# Params: state_abbr, year, offense_type
# Try: DEMO_KEY first, then registered key
```

**Fallback chain**:
1. FBI CDE (if working)
2. SpotCrime API (spotcrime.com/api) — ZIP-level, free tier
3. CityProtect (cityprotect.com) — city-level
4. Local PD open data portals (per-city, manual)

**Interface preserved**: `get_crime_score(zip_code) -> (score, confidence, source_name)`

---

### 5. Postgres Migration (`docker-compose.yml`, `settings.py`)

**docker-compose.yml**:
```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: prei
      POSTGRES_USER: prei
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports: ["5432:5432"]
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
  web:
    build: .
    depends_on: [db, redis]
    environment:
      DATABASE_URL: postgresql://prei:${POSTGRES_PASSWORD}@db:5432/prei
      CELERY_BROKER_URL: redis://redis:6379/0
```

**settings.py**: `DATABASE_URL` from env; remove SQLite default.

**Migration**: `python manage.py migrate` on fresh Postgres.

---

### 6. Celery + Redis (`core/celery.py`, `core/tasks.py`)

```python
# core/celery.py
app = Celery("prei")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks(["core.tasks"])
```

**Tasks to async**:
- `screening.re_screen_all(user_id)` — called from screening_settings view
- `discovery.process_discovery_batch(growth_area_id, source_keys)` — called from discovery view
- `vrm.scrape_state(state)` — called from VRM discovery

**Worker**: `celery -A core worker -l INFO -Q screening,discovery,vrm`

---

### 7. Team / Shared Pipeline (`core/models/team.py`)

```python
class Team(models.Model):
    name = models.CharField(max_length=100)
    owner = models.ForeignKey(User, related_name="owned_teams")
    created_at = models.DateTimeField(auto_now_add=True)

class TeamMembership(models.Model):
    ROLE_OWNER = "owner"
    ROLE_MEMBER = "member"
    ROLE_VIEWER = "viewer"
    ROLE_CHOICES = [...]
    team = models.ForeignKey(Team, related_name="memberships")
    user = models.ForeignKey(User)
    role = models.CharField(choices=ROLE_CHOICES)

class PipelineProperty(models.Model):
    # ... existing fields ...
    team = models.ForeignKey(Team, null=True, blank=True, on_delete=models.SET_NULL)
    # user FK retained for backward compat (personal pipelines)
```

**Views**: `/teams/`, `/teams/<pk>/invite/`, `/pipeline/` filtered by `team__memberships__user=request.user`.

---

### 8. Security Headers (`core/middleware/security_headers.py`)

```python
# Install django-csp
# settings.py:
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'", "cdn.jsdelivr.net")
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'", "fonts.googleapis.com")
CSP_FONT_SRC = ("'self'", "fonts.gstatic.com")
CSP_IMG_SRC = ("'self'", "data:")
CSP_CONNECT_SRC = ("'self'",)

PERMISSIONS_POLICY = {
    "geolocation": [],
    "camera": [],
    "microphone": [],
}

# Middleware order: SecurityMiddleware → CSPMiddleware → PermissionsPolicyMiddleware
```

**SRI**: Add `integrity` attr to all external `<script>`/`<link>` in `base.html`:
```html
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"
        integrity="sha384-..."></script>
```

---

## Data Flow

```
Rent Estimate Fallback Chain (screening):
┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ prop.rent    │──▶│ Rentcast     │──▶│ ATTOM        │──▶│ HUD FMR      │
│ (VRM only)   │   │ (by ZIP/addr)│   │ (if avail)   │   │ (by ZIP)     │
└──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘
     │                  │                  │                  │
     ▼                  ▼                  ▼                  ▼
  100% VRM          85% coverage       60% coverage       40% coverage
  coverage          (TX/FL/TN)         (where ATTOM)      (all metros)

GACS Validation:
historical GACS_t  ──▶ backtest script ──▶ weight grid ──▶ validated weights
FHFA/Zillow HPI    ──▶ 12mo forward     ──▶ search        ──▶ locked in prod
                      appreciation                                  + confidence bands

Async Screening:
User saves criteria ──▶ view.enqueue_task(screening.re_screen_all)
                      ──▶ Celery worker ──▶ processes batch
                      ──▶ WebSocket/poll ──▶ UI updates KPI cards
```

---

## Cross-Cutting Changes

| File | Change |
|---|---|
| `core/models/` | Add `Team`, `TeamMembership`; add `team` FK to `PipelineProperty` |
| `core/services/screening.py` | New rent fallback chain; Celery task for re-screen |
| `core/services/discovery.py` | Celery task for batch discovery |
| `core/integrations/sources/` | `rentcast_adapter.py`, extend `attom_adapter.py` |
| `core/integrations/market/` | `crime.py` rewrite, `schools.py` wire GreatSchools, `supply.py` new |
| `core/tasks.py` | Async task definitions |
| `core/celery.py` | Celery app config |
| `core/middleware/security_headers.py` | CSP, Permissions-Policy, CORP |
| `docker-compose.yml` | Postgres + Redis services |
| `settings.py` | DATABASE_URL, CELERY_BROKER_URL, CSP settings |
| `templates/base.html` | SRI on external scripts |

---

## Validation Checklist

- [ ] Rentcast spike: API key, coverage, latency
- [ ] ATTOM rent probe: field exists in Property API
- [ ] GACS backtest: R² ≥ 0.4 achievable
- [ ] Crime API: FBI CDE working or fallback identified
- [ ] docker-compose: Postgres + Redis + app healthy
- [ ] Celery: screening re-run < 5s user-visible
- [ ] Team invite: email → accept → shared pipeline visible
- [ ] ZAP scan: CSP/Permissions/CORP/SRI findings resolved

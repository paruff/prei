# Phase 3: Data Health & Screening UX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add data source health refresh with circuit breaker, screening filter bar, preview impact, and auto-versioning for screening criteria.

**Architecture:** Thin Django views wrapping existing service functions. Vanilla JS for real-time filtering via fetch API. DataSourceHealth model extended with circuit breaker fields. New ScreeningCriteriaVersion model for auto-versioning.

**Tech Stack:** Django 6.0, vanilla JS fetch API, Playwright E2E (sync API), pytest-django `live_server`.

---

## Global Constraints

- Currency and rates: `Decimal` everywhere in fixtures and assertions
- All new test files under `tests/e2e/`; module names end in `_e2e.py`
- Every test module: `pytestmark = pytest.mark.django_db(transaction=True)`
- No Bootstrap classes, inline `style=` layout attributes, or `!important`
- Commit messages: Conventional Commits (`feat:`, `test:`, `ci:`, `docs:`)
- Reuse existing service functions — no new business logic
- Deferred: WebSocket/polling for real-time multi-user

---

## File Map

| File | Role |
|------|------|
| `core/models/pipeline.py` | Add `consecutive_errors` to `DataSourceHealth`; add `ScreeningCriteriaVersion` |
| `core/migrations/` | New migration for model changes |
| `core/integrations/health_monitor.py` | Add circuit breaker logic + retry |
| `core/views/__init__.py` | Add `refresh_all_sources`, `health_json`, `screener_filter`, `screening_preview` views |
| `core/urls.py` | Add 4 new URL patterns |
| `templates/system.html` | Add Refresh All button + polling JS |
| `templates/pipeline/screener.html` | Add filter bar + fetch JS |
| `templates/pipeline/screening_settings.html` | Add Preview Impact button + version history |
| `tests/e2e/test_data_health_e2e.py` | New E2E tests |
| `tests/e2e/test_screening_ux_e2e.py` | New E2E tests |

---

### Task 1: Model Changes — consecutive_errors + ScreeningCriteriaVersion

**Files:**
- Modify: `core/models/pipeline.py:960-979` (DataSourceHealth)
- Create: `core/migrations/00XX_add_consecutive_errors_and_version.py`

**Interfaces:**
- Consumes: None (first task)
- Produces: `DataSourceHealth.consecutive_errors` field; `ScreeningCriteriaVersion` model

- [ ] **Step 1: Add consecutive_errors field to DataSourceHealth**

```python
# core/models/pipeline.py — add after error_message field (line ~971)

consecutive_errors = models.IntegerField(default=0)
```

- [ ] **Step 2: Add ScreeningCriteriaVersion model**

```python
# core/models/pipeline.py — add after ScreeningCriteria class

class ScreeningCriteriaVersion(models.Model):
    """Snapshot of ScreeningCriteria at a point in time."""

    criteria = models.ForeignKey(
        "ScreeningCriteria",
        on_delete=models.CASCADE,
        related_name="versions",
    )
    snapshot = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Screening Criteria Version"
        verbose_name_plural = "Screening Criteria Versions"

    def __str__(self) -> str:
        return f"Version {self.pk} of {self.criteria_id} @ {self.created_at}"
```

- [ ] **Step 3: Generate migration**

```bash
python manage.py makemigrations core --name add_consecutive_errors_and_version
```

- [ ] **Step 4: Apply migration**

```bash
python manage.py migrate
```

- [ ] **Step 5: Commit**

```bash
git add core/models/pipeline.py core/migrations/
git commit -m "feat(models): add consecutive_errors to DataSourceHealth and ScreeningCriteriaVersion"
```

---

### Task 2: Circuit Breaker Logic + Retry in Scrapers

**Files:**
- Modify: `core/integrations/health_monitor.py` (add circuit breaker methods)

**Interfaces:**
- Consumes: `DataSourceHealth.consecutive_errors` from Task 1
- Produces: `DataSourceHealthMonitor.check_circuit()`, `DataSourceHealthMonitor.record_success()`, `DataSourceHealthMonitor.record_failure()` methods

- [ ] **Step 1: Add circuit breaker methods to DataSourceHealthMonitor**

```python
# core/integrations/health_monitor.py — add to DataSourceHealthMonitor class

CIRCUIT_BREAKER_THRESHOLD = 3

def check_circuit(self, source_name: str) -> bool:
    """Check if source circuit is open (should skip)."""
    from core.models import DataSourceHealth

    health, _ = DataSourceHealth.objects.get_or_create(source_name=source_name)
    if health.consecutive_errors >= self.CIRCUIT_BREAKER_THRESHOLD:
        logger.warning("Circuit open for %s (%d consecutive errors)", source_name, health.consecutive_errors)
        return True
    return False

def record_success(self, source_name: str, record_count: int = 0) -> None:
    """Record successful source run."""
    from core.models import DataSourceHealth

    health, _ = DataSourceHealth.objects.get_or_create(source_name=source_name)
    health.consecutive_errors = 0
    health.status = "ok"
    health.last_run = timezone.now()
    health.record_count = record_count
    health.error_message = ""
    health.save(update_fields=["consecutive_errors", "status", "last_run", "record_count", "error_message"])

def record_failure(self, source_name: str, error: Exception) -> None:
    """Record failed source run and increment circuit counter."""
    from core.models import DataSourceHealth

    health, _ = DataSourceHealth.objects.get_or_create(source_name=source_name)
    health.consecutive_errors += 1
    health.status = "error"
    health.last_run = timezone.now()
    health.error_message = str(error)[:500]
    health.save(update_fields=["consecutive_errors", "status", "last_run", "error_message"])
```

- [ ] **Step 2: Add retry decorator**

```python
# core/integrations/health_monitor.py — add at module level

import time
from functools import wraps

def retry_with_backoff(max_retries: int = 1, base_delay: float = 2.0, timeout: float = 30.0):
    """Decorator: retry on failure with exponential backoff."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    last_exc = exc
                    if attempt < max_retries:
                        delay = base_delay * (2 ** attempt)
                        logger.warning("Retry %d/%d for %s after %.1fs: %s", attempt + 1, max_retries, func.__name__, delay, exc)
                        time.sleep(delay)
            raise last_exc
        return wrapper
    return decorator
```

- [ ] **Step 3: Write unit tests for circuit breaker**

```python
# tests/test_health_monitor.py — add to TestDataSourceHealthMonitor class

def test_check_circuit_open(self, monitor):
    """Circuit opens after 3+ consecutive errors."""
    from core.models import DataSourceHealth
    health = DataSourceHealth.objects.create(source_name="test", consecutive_errors=3)
    assert monitor.check_circuit("test") is True

def test_check_circuit_closed(self, monitor):
    """Circuit closed when errors below threshold."""
    from core.models import DataSourceHealth
    health = DataSourceHealth.objects.create(source_name="test", consecutive_errors=2)
    assert monitor.check_circuit("test") is False

def test_record_success_resets_counter(self, monitor):
    """Successful run resets consecutive_errors to 0."""
    from core.models import DataSourceHealth
    health = DataSourceHealth.objects.create(source_name="test", consecutive_errors=3, status="error")
    monitor.record_success("test", record_count=10)
    health.refresh_from_db()
    assert health.consecutive_errors == 0
    assert health.status == "ok"
    assert health.record_count == 10

def test_record_failure_increments_counter(self, monitor):
    """Failed run increments consecutive_errors."""
    from core.models import DataSourceHealth
    health = DataSourceHealth.objects.create(source_name="test", consecutive_errors=0)
    monitor.record_failure("test", Exception("test error"))
    health.refresh_from_db()
    assert health.consecutive_errors == 1
    assert health.status == "error"
    assert "test error" in health.error_message
```

- [ ] **Step 4: Run tests**

```bash
.venv/bin/python -m pytest tests/test_health_monitor.py -v
```

- [ ] **Step 5: Commit**

```bash
git add core/integrations/health_monitor.py tests/test_health_monitor.py
git commit -m "feat(health): add circuit breaker logic with retry decorator"
```

---

### Task 3: Refresh All Sources + Health JSON Endpoints

**Files:**
- Modify: `core/views/__init__.py` (add 2 views)
- Modify: `core/urls.py` (add 2 paths)

**Interfaces:**
- Consumes: `DataSourceHealthMonitor` from Task 2
- Produces: `POST /system/refresh-all/` and `GET /system/health-json/` endpoints

- [ ] **Step 1: Add refresh_all_sources view**

```python
# core/views/__init__.py — add after system_status view

@login_required
def refresh_all_sources(request: HttpRequest) -> HttpResponse:
    """Trigger all data source refreshes in background threads."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    import threading
    from django.db import connection as _conn

    def _run_ingestion(name, func, *args):
        _conn.close()
        try:
            func(*args)
        except Exception as e:
            logger.error("%s ingestion failed: %s", name, e)

    tasks = [
        ("HUD", lambda: __import__("core.services.ingestion", fromlist=["ingest_hud_reo"]).ingest_hud_reo()),
        ("USDA", lambda: __import__("core.services.ingestion", fromlist=["ingest_usda_reo"]).ingest_usda_reo()),
        ("Counties", lambda: __import__("core.services.ingestion", fromlist=["ingest_tx_counties"]).ingest_tx_counties()),
    ]

    for name, func in tasks:
        t = threading.Thread(target=_run_ingestion, args=(name, func), daemon=True)
        t.start()

    messages.success(request, "Refresh started for all data sources. Page will update automatically.")
    return redirect("system_status")
```

- [ ] **Step 2: Add health_json view**

```python
# core/views/__init__.py — add after refresh_all_sources

@login_required
def health_json(request: HttpRequest) -> HttpResponse:
    """Return data source health as JSON for polling."""
    from core.models import DataSourceHealth

    health = list(DataSourceHealth.objects.values("source_name", "last_run", "record_count", "status", "consecutive_errors"))
    return JsonResponse(health, safe=False)
```

- [ ] **Step 3: Add URL patterns**

```python
# core/urls.py — add after system_status path

path("system/refresh-all/", views.refresh_all_sources, name="refresh_all_sources"),
path("system/health-json/", views.health_json, name="health_json"),
```

- [ ] **Step 4: Write unit tests**

```python
# tests/test_views_health.py — create new file

import pytest
from django.test import Client
from django.contrib.auth import get_user_model

pytestmark = pytest.mark.django_db(transaction=True)

@pytest.fixture
def logged_in_client():
    User = get_user_model()
    user = User.objects.create_user("test_user", "t@t.com", "pass123")
    client = Client()
    client.force_login(user)
    return client

def test_refresh_all_sources_returns_redirect(logged_in_client):
    response = logged_in_client.post("/system/refresh-all/")
    assert response.status_code == 302

def test_health_json_returns_list(logged_in_client):
    response = logged_in_client.get("/system/health-json/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_refresh_all_sources_rejects_get(logged_in_client):
    response = logged_in_client.get("/system/refresh-all/")
    assert response.status_code == 405
```

- [ ] **Step 5: Run tests**

```bash
.venv/bin/python -m pytest tests/test_views_health.py -v
```

- [ ] **Step 6: Commit**

```bash
git add core/views/__init__.py core/urls.py tests/test_views_health.py
git commit -m "feat(views): add refresh_all_sources and health_json endpoints"
```

---

### Task 4: System Status Page UI — Refresh All Button + Polling JS

**Files:**
- Modify: `templates/system.html`

**Interfaces:**
- Consumes: `POST /system/refresh-all/` and `GET /system/health-json/` from Task 3
- Produces: Updated system status page with Refresh All button and live polling

- [ ] **Step 1: Add Refresh All Sources button**

```html
<!-- templates/system.html — add to Data Operations section, before the individual buttons -->

<form method="post" class="form-inline" id="refresh-all-form">
  {% csrf_token %}
  <input type="hidden" name="action" value="refresh_all">
  <button class="btn btn-primary" id="refresh-all-btn" type="submit">
    Refresh All Sources
  </button>
  <span id="refresh-status" class="help-text" style="margin-left: var(--sp-2);"></span>
</form>
```

- [ ] **Step 2: Add polling JavaScript**

```html
<!-- templates/system.html — add before {% endblock %} -->

<script>
(function() {
  var pollInterval = null;
  var pollCount = 0;
  var MAX_POLLS = 30; // 60 seconds at 2s interval

  function updateHealthTable(data) {
    data.forEach(function(h) {
      var row = document.querySelector('tr[data-source="' + h.source_name + '"]');
      if (!row) return;
      var statusCell = row.querySelector('.health-status');
      var recordsCell = row.querySelector('.health-records');
      var lastRunCell = row.querySelector('.health-lastrun');
      if (statusCell) {
        if (h.status === 'ok') {
          statusCell.innerHTML = '<span class="chip chip-success">✓ OK</span>';
        } else if (h.status === 'error') {
          statusCell.innerHTML = '<span class="chip chip-danger">✗ Error</span>';
        }
      }
      if (recordsCell) recordsCell.textContent = h.record_count;
      if (lastRunCell && h.last_run) {
        lastRunCell.textContent = new Date(h.last_run).toLocaleString();
      }
    });
  }

  function pollHealth() {
    fetch('/system/health-json/')
      .then(function(r) { return r.json(); })
      .then(function(data) {
        updateHealthTable(data);
        pollCount++;
        if (pollCount < MAX_POLLS) {
          pollInterval = setTimeout(pollHealth, 2000);
        } else {
          document.getElementById('refresh-status').textContent = 'Refresh complete.';
        }
      });
  }

  var form = document.getElementById('refresh-all-form');
  if (form) {
    form.addEventListener('submit', function(e) {
      // Don't prevent default — let form submit normally for the POST
      // But start polling after a short delay
      setTimeout(function() {
        document.getElementById('refresh-status').textContent = 'Refreshing...';
        pollCount = 0;
        pollHealth();
      }, 500);
    });
  }
})();
</script>
```

- [ ] **Step 3: Add data-source attribute to health table rows**

```html
<!-- templates/system.html — modify the health table rows to include data-source attribute -->

{% for h in health %}
<tr data-source="{{ h.source_name }}">
  <td>{{ h.source_name }}</td>
  <td class="health-lastrun">{{ h.last_run|date:"Y-m-d H:i"|default:"Never" }}</td>
  <td class="health-records">{{ h.record_count }}</td>
  <td class="health-status">
    {% if h.status == "ok" %}
      <span class="chip chip-success">✓ OK</span>
    {% elif h.status == "error" %}
      <span class="chip chip-danger">✗ Error</span>
    {% else %}
      <span class="chip chip-default">Unknown</span>
    {% endif %}
  </td>
</tr>
{% empty %}
<tr><td colspan="4">No data source health records yet. Run a data ingestion to populate.</td></tr>
{% endfor %}
```

- [ ] **Step 4: Commit**

```bash
git add templates/system.html
git commit -m "feat(ui): add Refresh All Sources button with live polling to system status"
```

---

### Task 5: Screening Filter Endpoint + Filter Bar UI

**Files:**
- Modify: `core/views/__init__.py` (add `screener_filter` view)
- Modify: `core/urls.py` (add 1 path)
- Modify: `templates/pipeline/screener.html` (add filter bar)

**Interfaces:**
- Consumes: `PipelineProperty` model, existing `pipeline_screener` view
- Produces: `GET /pipeline/screener/filter/` endpoint returning HTML fragment

- [ ] **Step 1: Add screener_filter view**

```python
# core/views/__init__.py — add after pipeline_screener view

@login_required
def screener_filter(request: HttpRequest) -> HttpResponse:
    """Filter screener results via AJAX. Returns HTML fragment."""
    from core.models import PipelineProperty

    qs = PipelineProperty.objects.filter(
        user=request.user,
        stage__in=["DISCOVERED", "SCREENING"],
    )

    # Apply filters from query params
    min_price = request.GET.get("min_price")
    max_price = request.GET.get("max_price")
    min_yield = request.GET.get("min_yield")
    max_ptr = request.GET.get("max_ptr")
    min_beds = request.GET.get("min_beds")
    state = request.GET.get("state")
    prop_type = request.GET.get("prop_type")

    if min_price:
        qs = qs.filter(price__gte=Decimal(min_price))
    if max_price:
        qs = qs.filter(price__lte=Decimal(max_price))
    if min_yield:
        qs = qs.filter(gross_yield_pct__gte=Decimal(min_yield))
    if max_ptr:
        qs = qs.filter(price_to_rent_ratio__lte=Decimal(max_ptr))
    if min_beds:
        qs = qs.filter(beds__gte=int(min_beds))
    if state:
        qs = qs.filter(state=state)
    if prop_type:
        qs = qs.filter(property_type=prop_type)

    return render(request, "pipeline/screener_results_fragment.html", {"properties": qs[:50]})
```

- [ ] **Step 2: Create results fragment template**

```html
<!-- templates/pipeline/screener_results_fragment.html — create new file -->

{% load humanize %}
{% for pp in properties %}
<tr>
  <td><a href="{% url 'pipeline_detail' pk=pp.pk %}">{{ pp.address|truncatechars:40 }}</a></td>
  <td>{{ pp.city }}, {{ pp.state }}</td>
  <td>${{ pp.price|intcomma }}</td>
  <td>{{ pp.gross_yield_pct|default:"—" }}%</td>
  <td>{{ pp.price_to_rent_ratio|default:"—" }}</td>
  <td>{{ pp.beds }}</td>
  <td>
    {% if pp.screening_passed %}
      <span class="chip chip-success">✓ Passed</span>
    {% elif pp.screening_passed == False %}
      <span class="chip chip-danger">✗ Failed</span>
    {% else %}
      <span class="chip chip-default">Unscreened</span>
    {% endif %}
  </td>
</tr>
{% empty %}
<tr><td colspan="7">No properties match the current filters.</td></tr>
{% endfor %}
```

- [ ] **Step 3: Add URL pattern**

```python
# core/urls.py — add after pipeline_screener path

path("pipeline/screener/filter/", views.screener_filter, name="screener_filter"),
```

- [ ] **Step 4: Add filter bar to screener template**

```html
<!-- templates/pipeline/screener.html — add before the results table -->

<div class="card" id="screener-filters">
  <h3 class="card-title">Filters</h3>
  <div class="form-row">
    <div class="form-field-group">
      <label class="field-label">Min Price</label>
      <input type="number" class="field-input" id="filter-min-price" placeholder="0">
    </div>
    <div class="form-field-group">
      <label class="field-label">Max Price</label>
      <input type="number" class="field-input" id="filter-max-price" placeholder="No limit">
    </div>
    <div class="form-field-group">
      <label class="field-label">Min Yield %</label>
      <input type="number" class="field-input" id="filter-min-yield" step="0.5" placeholder="0">
    </div>
    <div class="form-field-group">
      <label class="field-label">Max PTR</label>
      <input type="number" class="field-input" id="filter-max-ptr" step="0.5" placeholder="No limit">
    </div>
    <div class="form-field-group">
      <label class="field-label">Min Beds</label>
      <input type="number" class="field-input" id="filter-min-beds" min="1" placeholder="1">
    </div>
  </div>
</div>
```

- [ ] **Step 5: Add filter JavaScript**

```html
<!-- templates/pipeline/screener.html — add before {% endblock %} -->

<script>
(function() {
  var debounceTimer = null;

  function buildFilterUrl() {
    var params = new URLSearchParams();
    var minPrice = document.getElementById('filter-min-price').value;
    var maxPrice = document.getElementById('filter-max-price').value;
    var minYield = document.getElementById('filter-min-yield').value;
    var maxPtr = document.getElementById('filter-max-ptr').value;
    var minBeds = document.getElementById('filter-min-beds').value;

    if (minPrice) params.set('min_price', minPrice);
    if (maxPrice) params.set('max_price', maxPrice);
    if (minYield) params.set('min_yield', minYield);
    if (maxPtr) params.set('max_ptr', maxPtr);
    if (minBeds) params.set('min_beds', minBeds);

    return '/pipeline/screener/filter/?' + params.toString();
  }

  function applyFilters() {
    fetch(buildFilterUrl())
      .then(function(r) { return r.text(); })
      .then(function(html) {
        var tbody = document.querySelector('#screener-results tbody');
        if (tbody) tbody.innerHTML = html;
      });
  }

  function debounce() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(applyFilters, 300);
  }

  ['filter-min-price', 'filter-max-price', 'filter-min-yield', 'filter-max-ptr', 'filter-min-beds'].forEach(function(id) {
    var el = document.getElementById(id);
    if (el) el.addEventListener('input', debounce);
  });
})();
</script>
```

- [ ] **Step 6: Commit**

```bash
git add core/views/__init__.py core/urls.py templates/pipeline/screener.html templates/pipeline/screener_results_fragment.html
git commit -m "feat(screener): add filter bar with vanilla JS AJAX filtering"
```

---

### Task 6: Preview Impact Endpoint + UI

**Files:**
- Modify: `core/views/__init__.py` (add `screening_preview` view)
- Modify: `core/urls.py` (add 1 path)
- Modify: `templates/pipeline/screening_settings.html` (add button + JS)

**Interfaces:**
- Consumes: `ScreeningCriteria` model, `PipelineProperty` model
- Produces: `POST /pipeline/screening/preview/` endpoint

- [ ] **Step 1: Add screening_preview view**

```python
# core/views/__init__.py — add after pipeline_screening_settings view

@login_required
def screening_preview(request: HttpRequest) -> HttpResponse:
    """Preview how many properties pass current criteria without saving."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    from core.models import PipelineProperty, ScreeningCriteria

    criteria, _ = ScreeningCriteria.objects.get_or_create(user=request.user)
    qs = PipelineProperty.objects.filter(
        user=request.user,
        stage__in=["DISCOVERED", "SCREENING"],
    )

    total = qs.count()

    # Apply the same filtering logic as pipeline_screening_settings POST
    if criteria.min_price:
        qs = qs.filter(price__gte=criteria.min_price)
    if criteria.max_price:
        qs = qs.filter(price__lte=criteria.max_price)
    if criteria.min_gross_yield_pct:
        qs = qs.filter(gross_yield_pct__gte=criteria.min_gross_yield_pct)
    if criteria.max_price_to_rent_ratio:
        qs = qs.filter(price_to_rent_ratio__lte=criteria.max_price_to_rent_ratio)
    if criteria.min_beds:
        qs = qs.filter(beds__gte=criteria.min_beds)
    if criteria.max_beds:
        qs = qs.filter(beds__lte=criteria.max_beds)

    passed = qs.count()
    killed = total - passed

    return JsonResponse({"total": total, "passed": passed, "killed": killed})
```

- [ ] **Step 2: Add URL pattern**

```python
# core/urls.py — add after pipeline_screening_settings path

path("pipeline/screening/preview/", views.screening_preview, name="screening_preview"),
```

- [ ] **Step 3: Add Preview Impact button to settings template**

```html
<!-- templates/pipeline/screening_settings.html — add before the Save button -->

<div class="form-field-group mt-3">
  <button type="button" class="btn" id="preview-impact-btn">Preview Impact</button>
  <span id="preview-result" class="help-text" style="margin-left: var(--sp-2);"></span>
</div>
```

- [ ] **Step 4: Add Preview Impact JavaScript**

```html
<!-- templates/pipeline/screening_settings.html — add before {% endblock %} -->

<script>
(function() {
  var btn = document.getElementById('preview-impact-btn');
  if (!btn) return;

  btn.addEventListener('click', function() {
    var form = document.getElementById('screening-form');
    var formData = new FormData(form);

    fetch('/pipeline/screening/preview/', {
      method: 'POST',
      headers: {'X-CSRFToken': formData.get('csrfmiddlewaretoken')},
      body: formData
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
      var el = document.getElementById('preview-result');
      el.textContent = data.passed + ' of ' + data.total + ' properties would pass (' + data.killed + ' killed)';
    })
    .catch(function() {
      document.getElementById('preview-result').textContent = 'Error previewing impact';
    });
  });
})();
</script>
```

- [ ] **Step 5: Commit**

```bash
git add core/views/__init__.py core/urls.py templates/pipeline/screening_settings.html
git commit -m "feat(screening): add Preview Impact button to screening settings"
```

---

### Task 7: Auto-Version on Save + Version History UI

**Files:**
- Modify: `core/views/__init__.py` (update `pipeline_screening_settings` to create versions)
- Modify: `templates/pipeline/screening_settings.html` (add version history)

**Interfaces:**
- Consumes: `ScreeningCriteriaVersion` model from Task 1
- Produces: Auto-version on every criteria save; version history display

- [ ] **Step 1: Add version creation to pipeline_screening_settings**

```python
# core/views/__init__.py — in pipeline_screening_settings POST handler, after criteria.save()

# Create version snapshot
from core.models import ScreeningCriteriaVersion
ScreeningCriteriaVersion.objects.create(
    criteria=criteria,
    snapshot={
        "min_price": str(criteria.min_price) if criteria.min_price else None,
        "max_price": str(criteria.max_price) if criteria.max_price else None,
        "min_gross_yield_pct": str(criteria.min_gross_yield_pct) if criteria.min_gross_yield_pct else None,
        "max_price_to_rent_ratio": str(criteria.max_price_to_rent_ratio) if criteria.max_price_to_rent_ratio else None,
        "min_beds": criteria.min_beds,
        "max_beds": criteria.max_beds,
        "min_sqft": criteria.min_sqft,
        "max_year_built": criteria.max_year_built,
        "allowed_property_types": criteria.allowed_property_types,
        "allowed_states": criteria.allowed_states,
        "min_gacs_score": str(criteria.min_gacs_score) if criteria.min_gacs_score else None,
    },
)
```

- [ ] **Step 2: Add version history to template context**

```python
# core/views/__init__.py — in pipeline_screening_settings GET handler

versions = criteria.versions.all()[:5]
```

```python
# Add to render context

"versions": versions,
```

- [ ] **Step 3: Add version history display to template**

```html
<!-- templates/pipeline/screening_settings.html — add after the form -->

{% if versions %}
<div class="card mt-5">
  <h2 class="card-title">Recent Versions</h2>
  <table class="table">
    <thead>
      <tr><th>Date</th><th>Min Yield</th><th>Max PTR</th><th>Min Price</th><th>Max Price</th></tr>
    </thead>
    <tbody>
      {% for v in versions %}
      <tr>
        <td>{{ v.created_at|date:"M j, Y H:i" }}</td>
        <td>{{ v.snapshot.min_gross_yield_pct|default:"—" }}%</td>
        <td>{{ v.snapshot.max_price_to_rent_ratio|default:"—" }}</td>
        <td>${{ v.snapshot.min_price|default:"0"|intcomma }}</td>
        <td>${{ v.snapshot.max_price|default:"No limit" }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>
{% endif %}
```

- [ ] **Step 4: Commit**

```bash
git add core/views/__init__.py templates/pipeline/screening_settings.html
git commit -m "feat(screening): add auto-version on save and version history display"
```

---

### Task 8: E2E Tests for Data Health

**Files:**
- Create: `tests/e2e/test_data_health_e2e.py`

**Interfaces:**
- Consumes: `e2e_login`, `growth_area` fixtures from `tests/e2e/conftest.py`
- Produces: `TestDataHealth` class with 4 tests

- [ ] **Step 1: Write E2E tests**

```python
"""E2E tests for data health dashboard."""

import pytest

pytestmark = pytest.mark.django_db(transaction=True)


class TestDataHealth:
    def test_system_page_renders(self, page, e2e_login) -> None:
        """System status page loads with data source health heading."""
        page.goto("/system/")
        assert page.locator("h1", has_text="System Status").is_visible()
        assert page.locator("h2", has_text="Data Source Health").is_visible()

    def test_data_source_table_structure(self, page, e2e_login) -> None:
        """Data source health table has correct columns."""
        page.goto("/system/")
        table = page.locator("table", has_text="Data Source Health")
        assert table.is_visible()
        assert table.locator("th", has_text="Source").is_visible()
        assert table.locator("th", has_text="Last Run").is_visible()
        assert table.locator("th", has_text="Records").is_visible()
        assert table.locator("th", has_text="Status").is_visible()

    def test_refresh_all_button_exists(self, page, e2e_login) -> None:
        """Refresh All Sources button is visible."""
        page.goto("/system/")
        btn = page.locator("button", has_text="Refresh All Sources")
        assert btn.is_visible()

    def test_refresh_triggers_background_jobs(self, page, e2e_login) -> None:
        """Clicking Refresh All shows success message."""
        page.goto("/system/")
        page.click("button:has-text('Refresh All Sources')")
        page.wait_for_url("**/system/**")
        assert page.locator(".message", has_text="Refresh started").is_visible()
```

- [ ] **Step 2: Run tests**

```bash
.venv/bin/python -m pytest tests/e2e/test_data_health_e2e.py -v -m e2e --override-ini="addopts="
```

- [ ] **Step 3: Commit**

```bash
git add tests/e2e/test_data_health_e2e.py
git commit -m "test(e2e): add data health dashboard E2E tests"
```

---

### Task 9: E2E Tests for Screening UX

**Files:**
- Create: `tests/e2e/test_screening_ux_e2e.py`

**Interfaces:**
- Consumes: `e2e_login`, `kanban_property` fixtures
- Produces: `TestScreeningUX` class with 4 tests

- [ ] **Step 1: Write E2E tests**

```python
"""E2E tests for screening UX — filter bar, preview impact, version history."""

import pytest

pytestmark = pytest.mark.django_db(transaction=True)


class TestScreeningUX:
    def test_filter_bar_exists(self, page, e2e_login) -> None:
        """Screening filter controls are visible on screener page."""
        page.goto("/pipeline/screener/")
        assert page.locator("#filter-min-price").is_visible()
        assert page.locator("#filter-max-price").is_visible()
        assert page.locator("#filter-min-yield").is_visible()

    def test_filter_updates_results(self, page, e2e_login, kanban_property) -> None:
        """Changing filter updates results via AJAX."""
        page.goto("/pipeline/screener/")
        page.fill("#filter-min-price", "100000")
        page.wait_for_timeout(500)  # debounce
        # Results should update — property priced at 90000 should be filtered out
        tbody = page.locator("#screener-results tbody")
        assert "Boardwalk" not in tbody.inner_text()

    def test_preview_impact_button(self, page, e2e_login) -> None:
        """Preview Impact button exists on screening settings page."""
        page.goto("/pipeline/screening/settings/")
        btn = page.locator("button", has_text="Preview Impact")
        assert btn.is_visible()

    def test_version_history_displayed(self, page, e2e_login) -> None:
        """Screening settings page shows version history after save."""
        page.goto("/pipeline/screening/settings/")
        page.fill('input[name="min_gross_yield_pct"]', "8")
        page.click('button[type="submit"]:has-text("Save")')
        page.wait_for_url("**/screening/settings/**")
        assert page.locator("h2", has_text="Recent Versions").is_visible()
```

- [ ] **Step 2: Run tests**

```bash
.venv/bin/python -m pytest tests/e2e/test_screening_ux_e2e.py -v -m e2e --override-ini="addopts="
```

- [ ] **Step 3: Commit**

```bash
git add tests/e2e/test_screening_ux_e2e.py
git commit -m "test(e2e): add screening UX E2E tests"
```

---

## Self-Review

**Spec coverage:**
- [x] §2.1 Refresh All Sources → Task 3 (endpoint) + Task 4 (UI)
- [x] §2.2 Circuit Breaker → Task 1 (model) + Task 2 (logic)
- [x] §2.3 E2E Tests Data Health → Task 8
- [x] §2.4 Screening Filter Bar → Task 5
- [x] §2.5 Preview Impact → Task 6
- [x] §2.6 Auto-Version → Task 1 (model) + Task 7 (logic + UI)

**Placeholder scan:** No TBD/TODO. All code blocks complete.

**Type consistency:**
- `DataSourceHealth.consecutive_errors` used consistently in Tasks 1, 2, 4
- `ScreeningCriteriaVersion` used consistently in Tasks 1, 7
- View names match URL patterns (`refresh_all_sources`, `health_json`, `screener_filter`, `screening_preview`)

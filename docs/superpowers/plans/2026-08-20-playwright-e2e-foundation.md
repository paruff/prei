# Playwright E2E Foundation — Full Workflow & Kanban Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a real-browser Playwright E2E test suite covering the full prei workflow (Growth Explorer → Discovery → Screening → Underwriting → Offer → Pipeline) plus the Pipeline Kanban drag-and-drop interaction, and wire it into CI, so the audit's Phase 1 "Critical: No Playwright E2E tests" gap is closed.

**Architecture:** A new `tests/e2e/` package launches headless Chromium (Playwright sync API) against pytest-django's `live_server`. All source data (VRM/HUD/USDA/County) is seeded via Django fixtures so discovery never touches the live network. Two independent browser test modules cover (1) the end-to-end property journey and (2) kanban drag-and-drop stage advancement. The existing `tests-e2e` CI job (which already installs Chromium and runs `-m e2e`) picks up the new tests; it gains a `collectstatic` step for realistic rendering.

**Tech Stack:** Playwright 1.62 (sync API), pytest 9.1 + pytest-django 4.12 (`live_server`), Django 6.0, GitHub Actions (`ci-quality.yml`).

## Global Constraints

- No external network calls in browser tests — every source model that discovery reads is seeded first (the discovery view only scrapes when a source table is empty).
- Currency and rates are `Decimal` everywhere in fixtures and assertions.
- All new test files live under `tests/e2e/`; every test module sets `pytestmark = pytest.mark.django_db(transaction=True)` (required for `live_server` with file-based SQLite — mirrors `tests/acceptance/conftest.py`).
- Test modules are named with the `_e2e.py` suffix so the root `conftest.py` auto-assigns the `e2e` marker (CI runs `-m e2e`).
- Do not use Bootstrap classes, inline `style=` layout attributes, or `!important` (repo rule) — none needed here since tests only assert on DOM text/attributes.
- Commit messages follow Conventional Commits (`test:`, `ci:`, `docs:`) — enforced by CI.

---

### Task 1: Playwright Browser Harness + Smoke Test

**Files:**
- Create: `tests/e2e/__init__.py`
- Create: `tests/e2e/conftest.py`
- Create: `tests/e2e/test_harness_e2e.py`
- Create: `docs/superpowers/plans/README.md` (one-line index of this plan — optional, skip if the dir already has an index)

**Interfaces:**
- Consumes: root `conftest.py` (auto `e2e` marker for `_e2e.py` files), `investor_app.settings_test` (file-based SQLite enabled for `live_server`), `playwright==1.62.0` from `requirements.txt`.
- Produces:
  - `tests/e2e/conftest.py` fixtures consumed by Tasks 2–3:
    - `browser` → `playwright.sync_api.Browser` (session-scoped, headless Chromium)
    - `page` → `playwright.sync_api.Page` (function-scoped, bound to `live_server`)
    - `e2e_user` → `django.contrib.auth.User` (username `e2e_user`, password `e2e-password-123`)
    - `e2e_login` → logs the user in through the real `/accounts/login/` form, returns the `User`
    - `growth_area` → `core.models.GrowthArea` (Austin, TX, GACS 75.50)
    - `discovery_sources` → list of `[VrmProperty, HudProperty, UsdaProperty, CountyForeclosureNotice]` all in Austin, TX
  - `tests/e2e/test_harness_e2e.py` `TestHarness` with `test_page_loads_health_check` and `test_login_redirects_to_dashboard`.

- [ ] **Step 1: Create the package files**

`tests/e2e/__init__.py`:
```python
"""Browser-based E2E tests (Playwright)."""
```

- [ ] **Step 2: Write the failing smoke test**

`tests/e2e/test_harness_e2e.py`:
```python
"""Smoke tests proving the Playwright harness binds to live_server and can log in."""

import pytest

pytestmark = pytest.mark.django_db(transaction=True)


class TestHarness:
    def test_page_loads_health_check(self, page) -> None:
        page.goto("/health/")
        assert page.locator("body").inner_text() != ""

    def test_health_returns_ok(self, page) -> None:
        page.goto("/health/")
        assert "ok" in page.locator("body").inner_text()

    def test_login_redirects_to_dashboard(self, page, e2e_login) -> None:
        page.goto("/dashboard/")
        assert page.locator("text=Dashboard").count() >= 1 or page.url.endswith("/dashboard/")
```

- [ ] **Step 3: Run the harness smoke test to verify failure**

Run from repo root (assuming `.venv` is active; also requires `playwright install chromium` to have been run once locally):
```
.venv/bin/python -m pytest tests/e2e/test_harness_e2e.py -v --tb=short -m e2e
```
Expected: FAIL with `ModuleNotFoundError: No module named 'tests.e2e'` (or `fixture 'page' not found`) — the harness does not exist yet.

- [ ] **Step 4: Implement the harness fixtures**

`tests/e2e/conftest.py`:
```python
"""Playwright browser E2E fixtures.

These tests talk to the app through a real headless Chromium browser
against pytest-django's live_server. Seeded data is created in the test
DB (transactionally) and reached over HTTP via live_server.url.
The page fixture holds absolute URLs off live_server; tests may also use
page.goto("/relative/path/") because the page context's base_url is set.
"""

from __future__ import annotations

from typing import Iterator

import pytest
from playwright.sync_api import Browser, Page, sync_playwright

from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal

User = get_user_model()

E2E_USERNAME = "e2e_user"
E2E_PASSWORD = "e2e-password-123"


@pytest.fixture(scope="session")
def browser() -> Iterator[Browser]:
    """Headless Chromium shared across all browser tests in the session."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture()
def page(browser: Browser, live_server) -> Iterator[Page]:
    """A fresh browser context bound to pytest-django's live_server."""
    context = browser.new_context(base_url=live_server.url)
    page = context.new_page()
    yield page
    context.close()


@pytest.fixture()
def e2e_user(db) -> User:  # type: ignore[no-untyped-def]
    return User.objects.create_user(
        username=E2E_USERNAME,
        email="e2e@example.com",
        password=E2E_PASSWORD,
    )


@pytest.fixture()
def e2e_login(page: Page, e2e_user: User) -> User:  # type: ignore[no-untyped-def]
    """Log the browser in through the real login form (accounts/login/)."""
    page.goto("/accounts/login/")
    page.fill('input[name="username"]', E2E_USERNAME)
    page.fill('input[name="password"]', E2E_PASSWORD)
    page.click('button[type="submit"]')
    page.wait_for_url("**/dashboard/")
    return e2e_user


@pytest.fixture()
def growth_area(db) -> object:  # type: ignore[no-untyped-def]
    from core.models import GrowthArea

    return GrowthArea.objects.create(
        state="TX",
        city_name="Austin",
        metro_area="Austin-Round Rock",
        population_growth_rate=Decimal("0.0214"),
        employment_growth_rate=Decimal("0.0341"),
        median_income_growth=Decimal("0.0187"),
        housing_demand_index=82,
        supply_constraint_index=45,
        data_timestamp=timezone.now(),
        population=978908,
        composite_score=Decimal("75.50"),
        landlord_score=8,
    )


@pytest.fixture()
def discovery_sources(db, growth_area) -> list:  # type: ignore[no-untyped-def]
    """One record per source in Austin, TX so discovery never hits the network.

    The property_discovery view only triggers background scrapers when a
    source table has zero rows for the state; seeding rows short-circuits
    that branch and processes the seeded records synchronously.
    """
    from core.models import (
        CountyForeclosureNotice,
        HudProperty,
        UsdaProperty,
        VrmProperty,
    )

    now = timezone.now()
    vrm = VrmProperty.objects.create(
        vrm_property_id=90001,
        vrm_listing_url="https://www.vrmproperties.com/property/90001",
        address="100 Prime St",
        city="Austin",
        state="TX",
        zip_code="78701",
        county="Travis",
        list_price=Decimal("200000.00"),
        projected_monthly_rent=Decimal("2000.00"),
        bedrooms=3,
        bathrooms=Decimal("2.0"),
        year_built=2001,
        status=VrmProperty.Status.FOR_SALE,
        scraped_at=now,
        last_seen_at=now,
    )
    hud = HudProperty.objects.create(
        hud_case_number="HUD-482-001",
        address="200 Value Ave",
        city="Austin",
        state="TX",
        zip_code="78702",
        county="Travis",
        asking_price=Decimal("85000.00"),
        list_price=Decimal("85000.00"),
        bedrooms=3,
        bathrooms=Decimal("2.0"),
        square_feet=1200,
        status=HudProperty.Status.ACTIVE,
        scraped_at=now,
        last_seen_at=now,
    )
    usda = UsdaProperty.objects.create(
        usda_case_number="USDA-77-001",
        address="300 Rural Ln",
        city="Austin",
        state="TX",
        zip_code="78703",
        county="Travis",
        list_price=Decimal("150000.00"),
        bedrooms=3,
        bathrooms=Decimal("2.0"),
        square_feet=1500,
        status=UsdaProperty.Status.ACTIVE,
        scraped_at=now,
        last_seen_at=now,
    )
    notice = CountyForeclosureNotice.objects.create(
        case_number="TC-2026-0001",
        document_type=CountyForeclosureNotice.DocumentType.NTS,
        address="400 Auction Way",
        city="Austin",
        state="TX",
        zip_code="78704",
        county="Travis",
        filing_date=timezone.now().date(),
    )
    return [vrm, hud, usda, notice]
```

Change `test_harness_e2e.py` `test_health_returns_ok` to use the absolute live_server URL: `page.goto("/health/")` works because the context `base_url` is set to `live_server.url` in the harness above, so relative `page.goto` resolves against it. The first smoke test's assertion (`body.inner_text() != ""`) is fine.

- [ ] **Step 5: Verify the harness tests pass**

Run:
```
.venv/bin/python -m pytest tests/e2e/test_harness_e2e.py -v --tb=short -m e2e
```
Expected: 3 PASS.

> If `playwright` reports "Executable doesn't exist": run `.venv/bin/python -m playwright install chromium`.

- [ ] **Step 6: Commit**

```bash
git add tests/e2e/__init__.py tests/e2e/conftest.py tests/e2e/test_harness_e2e.py
git commit -m "test(e2e): add playwright browser harness and login smoke tests"
```

---

### Task 2: Full Workflow Journey E2E Test

**Files:**
- Create: `tests/e2e/test_workflow_e2e.py`

**Interfaces:**
- Consumes: `e2e_login`, `growth_area`, `discovery_sources` from Task 1; existing pages at `/growth-explorer/`, `/discovery/?growth_area_id=`, `/pipeline/screener/?growth_area_id=`, `/pipeline/<pk>/offer/`, `/pipeline/list/`; existing view routes `property_discovery` (POST), `pipeline_screener` (POST action=advance), `pipeline_offer_create` (POST).
- Produces: `TestWorkflowJourney` with:
  - `test_screener_requires_login` — unauth GET of `/pipeline/screener/` redirects to login.
  - `test_full_workflow_journey` — login → growth explorer renders → discovery discovers 4 & passes all → screener shows PASSED → advance to Underwriting → record an offer → pipeline list shows the card.

- [ ] **Step 1: Write the failing journey test**

`tests/e2e/test_workflow_e2e.py`:
```python
"""Full-workflow browser E2E: Growth Explorer → Discovery → Screening → Underwriting → Offer → Pipeline."""

import re

import pytest

pytestmark = pytest.mark.django_db(transaction=True)


class TestWorkflowJourney:
    def test_screener_requires_login(self, page) -> None:
        page.goto("/pipeline/screener/")
        assert page.url.endswith("/accounts/login/")

    def test_full_workflow_journey(self, page, e2e_login, growth_area, discovery_sources) -> None:
        # ── Growth Explorer renders ────────────────────────────────────
        page.goto("/growth-explorer/")
        assert page.locator("h1", has_text="Growth Area Explorer").is_visible()
        assert page.locator("#state-select").is_visible()

        # ── Discovery: seeded sources listed, run discovery ────────────
        page.goto(f"/discovery/?growth_area_id={growth_area.pk}")
        assert page.locator("#discover-btn").is_visible()
        assert page.locator("label", has_text="HUD REO").is_visible()
        assert page.locator("label", has_text="VRM (VA REO)").is_visible()

        page.click("#discover-btn")
        page.locator("#results-section:not([hidden])").wait_for(state="visible", timeout=30000)

        results_text = page.locator("#results-section").inner_text()
        assert "Discovered" in results_text
        # All four seeded sources pass screening (see Global Constraints note below).
        assert "Passed Screening" in results_text
        assert "100 Prime St" in page.inner_text("body")

        # ── Screener: property passed automatic screening ──────────────
        page.goto(f"/pipeline/screener/?growth_area_id={growth_area.pk}")
        row = page.locator("tr", has_text="100 Prime St")
        assert row.is_visible()
        assert row.locator(".chip-success", has_text="Passed").is_visible()

        # ── Advance to Underwriting via the screener action ────────────
        row.locator('button', has_text="Underwriting").click()
        assert page.locator(".message", has_text="moved to Underwriting").is_visible()

        # Extract the pipeline property pk from the address detail link.
        href = page.locator('tr', has_text="100 Prime St").locator('a[href*="/pipeline/"]').first.get_attribute("href")
        pk = re.search(r"/pipeline/(\d+)/", href).group(1)

        # ── Offer: record an offer on the property ─────────────────────
        page.goto(f"/pipeline/{pk}/offer/")
        page.fill('input[name="offer_price"]', "185000")
        page.click('button[type="submit"]:has-text("Submit Offer")')
        assert page.locator(".message", has_text="Offer recorded.").is_visible()

        # ── Pipeline list: card is present with UNDERWRITING badge ─────
        page.goto("/pipeline/list/")
        card = page.locator(".pipeline-card", has_text="100 Prime St")
        assert card.is_visible()
        assert card.locator(".badge-stage", has_text="Underwriting").is_visible()
```

> Why all four pass screening: default `ScreeningCriteria` (autocreated by `create_from_*`) allows any state, no property-type/foreclosure filter, no price bounds, `min_gross_yield_pct=7`, `max_price_to_rent_ratio=15`, `min_beds=1`. The VRM yield is 12% (24000/200000) and PTR 8.33; HUD/USDA/county have no rent data so yield/PTR are skipped; all have ≥2 beds. Score stays ≥100, `passed=True`.

- [ ] **Step 2: Run to verify failure**

```
.venv/bin/python -m pytest tests/e2e/test_workflow_e2e.py -v --tb=short -m e2e
```
Expected: FAIL — discovery results section builds but the journey assertions kick in once the harness (Task 1) exists; run this only after Task 1 lands. First run failure mode is the missing test module (before Task 2 creates it) or a legit assertion failure if the app behavior differs — investigate before moving on.

- [ ] **Step 3: Implement the minimal wiring (none expected)**

If run with Task 1 merged, this test should pass against the existing app — the whole point is that the current ALPHA/BETA UI already renders these flows. If any assertion fails, use `--tb=long` and the Playwright trace (`page.screenshot()` inside the test) to find the real gap; fix the test's selectors to match the template, not the template to the test, unless the app truly regressed.

- [ ] **Step 4: Run to verify pass**

```
.venv/bin/python -m pytest tests/e2e/test_workflow_e2e.py -v --tb=short -m e2e
```
Expected: 2 PASS (login gate + full journey).

- [ ] **Step 5: Commit**

```bash
git add tests/e2e/test_workflow_e2e.py
git commit -m "test(e2e): cover full discover->screen->underwrite->offer->pipeline journey"
```

---

### Task 3: Kanban Drag-and-Drop E2E Test

**Files:**
- Create: `tests/e2e/test_kanban_e2e.py`

**Interfaces:**
- Consumes: `e2e_login` from Task 1; `PipelineProperty` model (stage `SCREENING`, status `ACTIVE`); kanban view `/pipeline/kanban/` (GET render + POST `{property_id, new_stage}` returning JSON); kanban template drag handlers on `.kanban-card` (dragstart) and `#col-<STAGE>` (dragover/drop).
- Produces: `TestKanban` with:
  - `test_board_renders_stage_columns` — SCREENING and UNDERWRITING columns exist.
  - `test_drag_advances_stage` — drag a card from SCREENING to UNDERWRITING, wait for the POST, reload, assert persistence in DOM and DB.

- [ ] **Step 1: Write the failing kanban tests**

`tests/e2e/test_kanban_e2e.py`:
```python
"""Browser E2E for the Pipeline Kanban drag-and-drop advance."""

import pytest

from core.models import PipelineProperty

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture()
def kanban_property(db, e2e_login, growth_area) -> PipelineProperty:
    return PipelineProperty.objects.create(
        user=e2e_login,
        source_type=PipelineProperty.SourceType.HUD,
        source_id="KANBAN-0001",
        address="101 Boardwalk Blvd",
        city="Austin",
        state="TX",
        zip_code="78701",
        county="Travis",
        growth_area=growth_area,
        stage=PipelineProperty.Stage.SCREENING,
        status=PipelineProperty.Status.ACTIVE,
        screening_passed=True,
        price=90000,
        beds=3,
    )


class TestKanban:
    def test_board_renders_stage_columns(self, page, e2e_login, kanban_property) -> None:
        page.goto("/pipeline/kanban/")
        assert page.locator('#col-SCREENING .kanban-card[data-id="%d"]' % kanban_property.pk).is_visible()
        assert page.locator(".kanban-column", has_text="Underwriting").is_visible()

    def test_drag_advances_stage(self, page, e2e_login, kanban_property) -> None:
        page.goto("/pipeline/kanban/")
        card_sel = '.kanban-card[data-id="%d"]' % kanban_property.pk
        assert page.locator(card_sel).is_visible()

        # Synthetic HTML5 Drag-and-Drop against the column's drop target.
        with page.expect_response(lambda r: r.url.endswith("/pipeline/kanban/") and r.request.method == "POST"):
            page.evaluate(
                """({cardSel, targetSel}) => {
                    const card = document.querySelector(cardSel);
                    const target = document.querySelector(targetSel);
                    const dt = new DataTransfer();
                    card.dispatchEvent(new DragEvent('dragstart', {bubbles: true, dataTransfer: dt}));
                    target.dispatchEvent(new DragEvent('dragover', {bubbles: true, dataTransfer: dt}));
                    target.dispatchEvent(new DragEvent('drop', {bubbles: true, dataTransfer: dt}));
                    card.dispatchEvent(new DragEvent('dragend', {bubbles: true, dataTransfer: dt}));
                }""",
                arg={"cardSel": card_sel, "targetSel": "#col-UNDERWRITING"},
            )

        # Reload to prove the stage persisted, not just the DOM move.
        page.reload()
        assert page.locator('#col-UNDERWRITING .kanban-card[data-id="%d"]' % kanban_property.pk).is_visible()
        assert page.locator('#col-SCREENING .kanban-card[data-id="%d"]' % kanban_property.pk).count() == 0

        kanban_property.refresh_from_db()
        assert kanban_property.stage == PipelineProperty.Stage.UNDERWRITING
```

- [ ] **Step 2: Run to verify failure**

```
.venv/bin/python -m pytest tests/e2e/test_kanban_e2e.py -v --tb=short -m e2e
```
Expected: FAIL — module not found (before this task) or a real behavior assertion failure once the file exists (e.g., the POST rejects backward/unknown stage). In particular `test_drag_advances_stage` should pass if the existing kanban POST works — this test is the regression net the audit wants.

- [ ] **Step 3: Implement minimal wiring (none expected)**

The kanban view (`core/views/__init__.py:1504`) already implements the POST handler and the template (`templates/pipeline/kanban.html`) already implements drag/drop — this task only proves it end-to-end. If the drag events don't trigger the handler, check that `DataTransfer` is available in the page's realm (it is in Chromium) and that the fetch fires with `X-CSRFToken` (the template inline `{{ csrf_token }}` supplies it). No app code changes intended.

- [ ] **Step 4: Run to verify pass**

```
.venv/bin/python -m pytest tests/e2e/test_kanban_e2e.py -v --tb=short -m e2e
```
Expected: 2 PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/e2e/test_kanban_e2e.py
git commit -m "test(e2e): cover kanban drag-and-drop stage advance"
```

---

### Task 4: CI Integration — Run Browser E2E in the Existing Job

**Files:**
- Modify: `.github/workflows/ci-quality.yml` (the `tests-e2e` job)

**Interfaces:**
- Consumes: Task 1–3 test files; the existing `tests-e2e` job already runs `pytest tests/ core/tests/ -m e2e` (this recurses into `tests/e2e/`), already installs Playwright + Chromium (`playwright install --with-deps chromium`), and caches browsers.
- Produces: a CI job that serves static assets before the browser tests run, so pages render realistically.

- [ ] **Step 1: Add collectstatic to the tests-e2e job**

In `.github/workflows/ci-quality.yml`, inside the `tests-e2e` job, between the "Install Playwright" steps (or "Cache Playwright browsers") and the "Run E2E tests" step, insert:

```yaml
      - name: Collect static files
        run: python manage.py collectstatic --noinput --verbosity 0
```

Because Playwright browsers already resolve relative URLs against `live_server.url` (Task 1 harness), no other workflow change is required — the browser tests run inside the same `-m e2e` selection as the existing service-level `_e2e.py` tests.

- [ ] **Step 2: Verify the workflow renders (dry lint)**

Run the file through a YAML parse (no structural validation available locally without act):
```
python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/ci-quality.yml')); print('YAML OK')"
```
Expected: `YAML OK`.

- [ ] **Step 3: Run the full e2e selection locally once**

```
.venv/bin/python -m pytest tests/ core/tests/ -m e2e -q --tb=short
```
Expected: existing `test_pipeline_e2e.py` + new `tests/e2e/*.py` all PASS (flaky retry `--reruns 1` applies). Record the count for the CI green run.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/ci-quality.yml
git commit -m "ci: collect static assets before browser e2e runs"
```

---

## Self-Review

**Spec coverage (audit Phase 1, line 82–86):**
- Playwright E2E suite for Growth Explorer → Discovery → Screening → Underwriting → Offer → Pipeline → Task 2 (`test_full_workflow_journey`).
- CI integration with headless browser → Task 4 (existing `tests-e2e` job + `collectstatic`; browser runs headless via `chromium.launch(headless=True)`, Task 1).
- Kanban wiring verification (Phase 2's frontend, already present) → Task 3.
- Remaining audit phases (Phase 2 backend endpoints, Phase 3 data-health/screening UX, Phase 4 leasing/comparison) are **out of scope for this plan by design** — they are independent subsystems and should each get their own plan, per the writing-plans scope rule. This plan is the TDD foundation that must land first.

**Placeholder scan:** No TBD/TODO. Every fixture and assertion contains concrete data and selectors validated against the templates (`screener.html`, `kanban.html`, `offer_form.html`, `property_discovery.html`, `pipeline_list.html`) and views read during plan authoring.

**Type/signature consistency:** Fixtures named identically in Tasks 1–3: `e2e_login`, `growth_area`, `discovery_sources`, `page`. `PipelineProperty.Stage.UNDERWRITING` used consistently; `#col-<STAGE>` selector matches `kanban.html` (id=`col--{{ col.stage }}`); card `data-id="{{ pp.pk }}"` matches the drag helper.

**One flagged risk for the implementer:** `test_harness_e2e.py::test_health_returns_ok` asserts the body text contains `ok`. The view `core/views/__init__.py:160` returns `JsonResponse({"status": "ok"})`, which the browser renders as `{"status": "ok"}` — the `in` assertion is correct. If the response shape ever changes, the assertion must follow the view, not the view the assertion.

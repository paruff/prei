# Design: Phase A — CI/Test Quality Gaps

### A-2: BDD pipeline suite over real HTTP
`tests_bdd/steps/pipeline_acceptance_steps.py` swaps `django.test.Client` for
an `httpx.Client` bound to pytest-django's `live_server.url`. `Given` steps
keep building fixtures via the ORM; `tests_bdd/conftest.py`'s `_reset_ctx`
fixture depends on `transactional_db` (not `db`) so rows committed by the test
process are visible to the live server's background-thread request handling.
POST steps fetch a CSRF token from the target form page first (`_csrf_token()`
helper) since httpx doesn't auto-handle Django CSRF the way the test client
does.

### A-3: Acceptance suite runs pre-merge
`tests/acceptance/conftest.py`'s `base_url` fixture falls back to a
session-scoped `live_server` when `BASE_URL` is unset, lazily requested via
`request.getfixturevalue(...)` so `BASE_URL`-driven runs never touch Django's
DB fixtures. A separate autouse `_enable_db_for_live_server` fixture calls
`request.getfixturevalue("db")` per test function, since pytest-django blocks
DB access per-test regardless of a session-scoped fixture's own DB setup.
`ci-quality.yml`'s `acceptance-check` job drops `--collect-only` and runs the
suite for real, with `BASE_URL` intentionally unset.

### A-4: Real build-time budget
`build-image`'s `job-start` step persists its epoch to `$GITHUB_ENV`. The
"Check build time" step computes the elapsed duration against that epoch and
fails (`::error::` + `exit 1`) past 600s. `timeout-minutes: 10` on the job
itself is a hard backstop independent of the soft check.

### A-5: Response-shape validation
`schemas.py` gained two generic models — `LoginGateAssertion`
(`Literal[200, 302]`, for pages that redirect anonymous users to login) and
`NoCrashAssertion` (`status_code < 500`, for pages that must not error
regardless of auth state) — reused across the status-only files
(`test_brrrr.py`, `test_dashboard.py`, `test_pipeline.py`, `test_leasing.py`,
parts of `test_growth.py`/`test_property_pipeline.py`). Files with existing
purpose-built models (`LoginPageAssertion`, `DiscoveryPageAssertion`,
`StaticAssetAssertion` in `test_pages.py`; `GrowthAreasResponse` in
`test_growth.py`) now actually import and validate against them instead of
duplicating loose dict/status assertions.

### Bugs surfaced by A-3 (fixed, not scope creep — this is what the new gate is for)
- `pipeline_list` view was missing `@login_required`, unlike sibling
  `leasing_list`, causing a 500 instead of a redirect for anonymous access.
- `tests/acceptance/test_leasing.py` hardcoded a stale route (`/leasing/list/`
  instead of `/leasing/`) that had never actually executed under
  `--collect-only`.

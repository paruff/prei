# Repo Audit & Implementation Plan — 2026-07-27

> Fresh, evidence-based audit. Every finding below was reproduced locally against
> the current `main` (clean working tree, CI green) — this is not a rehash of
> `docs/TOP_01_PLAN.md` or `docs/KNOWN_LIMITATIONS.md`, though it references both
> where relevant. Nothing here is theoretical; each finding includes the command
> that produced it.

## Executive Summary

The repo is well-instrumented: pre-commit hooks, an 11-job PR gate, semantic
release, CodeQL, gitleaks, a documented security policy, and a change-impact
map. That maturity is real. But two of the automated gates that the project
relies on for "we're safe" assurance are **currently no-ops**, and nobody would
know without running them by hand:

1. **The Bandit security-lint gate (CI + pre-commit) passes by failing silently.**
   It scans almost no code on Python 3.14 and still reports "No issues
   identified." This is the most important finding in this audit — for
   financial software, a security gate that lies is worse than no gate.
2. **`mypy.ini` has a duplicate section that breaks any full-repo mypy run**,
   and a duplicate-module error blocks it further. CI is scoped narrowly
   enough to avoid it, so nobody's noticed.

Everything else found is real but lower severity: six already-documented,
still-open items in `SECURITY.md` (one HIGH), a test-invocation footgun that
makes the suite look broken when it isn't, and minor repo hygiene.

## Methodology

Verified directly against the working tree on 2026-07-27, branch `main`,
clean (`git status` — only a pre-existing untracked `.agents/logs/` file):

| Check | Command | Result |
|---|---|---|
| CI status | `gh run list --branch main --limit 8` | ✅ green (last 8 runs) |
| Full test suite | `pytest -q` (no filters) | 1842 passed, 44 failed, 4 errors — see [Finding 4](#finding-4-low--bare-pytest-invocation-is-a-false-alarm-generator) |
| Lint | `ruff check .` | ✅ clean |
| Type check (repo-scoped, as CI runs it) | `mypy core/ investor_app/finance/ ...` | not independently re-run; CI green |
| Type check (naive `mypy .`) | `mypy .` | ❌ fails immediately — see [Finding 2](#finding-2-high--mypyini-duplicate-section--conftest-collision-breaks-full-repo-type-check) |
| Security lint | `bandit -r core/ investor_app/ -x ".venv,migrations" -c .bandit -f txt` (exact CI invocation) | reports "No issues identified" while silently skipping ~60 files — see [Finding 1](#finding-1-critical--bandit-security-gate-is-silently-non-functional-on-python-314) |
| Dependency freshness | `pip list --outdated` | many dev-tool minor/patch versions behind; Dependabot already runs weekly — no action needed |
| Secrets tracked in git | `git check-ignore -v .env db.sqlite3 test_db.sqlite3 .coverage build-report.md ...` | all properly ignored |
| Tracked stray files | `git ls-files \| grep -E "db\.sqlite3\|\.coverage\|test_check\.db"` | `test_check.db` (0 bytes) is tracked — see [Finding 5](#finding-5-low--repo-hygiene) |

## Findings

### Finding 1 — CRITICAL — Bandit security gate is silently non-functional on Python 3.14

**Where:** `.github/workflows/ci-quality.yml` (`lint` job), `.pre-commit-config.yaml`
(bandit hook, rev `1.8.0`), `requirements.txt` (`bandit==1.8.0`).

**Evidence:**

```
$ bandit -r core/ investor_app/ -x ".venv,migrations" -c .bandit -f txt
[manager] ERROR  Exception occurred when executing tests against ./core/views_portfolio.py.
...
Test results:
    No issues identified.
Files skipped (1):
    ./core/views_portfolio.py (exception while scanning file)
```

The same exception fires for ~60 of the ~65 files bandit is asked to scan
(`core/tests/*.py`, `core/views/__init__.py`, `investor_app/settings.py`,
etc.). Root cause, from `bandit --debug`:

```
File ".../bandit/core/node_visitor.py", line 171, in visit_Str
    self.context["str"] = node.s
AttributeError: 'Constant' object has no attribute 's'
```

Python 3.14 removed the deprecated `ast.Constant.s`/`.n` compatibility
aliases. Bandit 1.8.0's `visit_Str`/`visit_Num` visitors still use them, so
bandit throws on the first string/number literal in a file, bandit's manager
catches the exception *per file* and marks it "skipped," and the run exits
0 with "No issues identified" — indistinguishable from a genuinely clean
scan. This is **not** a local-only artifact: CI pins the identical Python
version (`.github/actions/python-setup/action.yml` → `python-version: "3.14.6"`),
so the CI `lint` job and every pre-commit run on every developer machine
have been reporting the same false pass.

This is tracked upstream: [PyCQA/bandit#1219](https://github.com/PyCQA/bandit/issues/1219)
("Redo support for Python 3.14") is open as of this audit — a prior attempt
(#1189) shipped in 1.8.1, regressed (#1216), and was reverted in 1.8.2. There
is currently no released bandit version with confirmed working Python 3.14
AST support to pin to.

**Impact:** This project handles financial data and is explicit about
"AI writes, humans decide" governance (`AGENTS.md`) — the security-lint gate
existing and being trusted is part of how that governance works. Right now
it provides zero actual coverage while looking green.

**Recommended fix (do not just bump the version — verify it):**

1. **Immediate stopgap:** enable Ruff's `S` rule set (`flake8-bandit` port,
   already vendored in ruff, which runs cleanly on 3.14 per this audit's
   `ruff check .` run). Add `select = ["E4", "E7", "E9", "F", "S"]` (or use
   ruff's default+extend-select) to `.ruff.toml`, triage the initial findings,
   and use `# noqa: S###` for accepted risks. This restores *real* automated
   security-pattern coverage within a single PR, using a tool already in the
   pipeline.
2. **Make bandit fail loudly instead of silently:** until upstream 3.14
   support lands, add a guard step (e.g. `bandit ... 2>&1 | tee bandit.log &&
   ! grep -q "exception while scanning file" bandit.log`) to both the CI
   `lint` job and the pre-commit hook, so a skipped file breaks the gate
   instead of passing it. This converts today's silent failure into a loud,
   honest one while a fix is pending.
3. **Track the upstream issue** and swap back to bandit (or drop the Ruff
   stopgap) once #1219 ships and is verified locally with the same repro
   command above.
4. Update `SECURITY.md` §4.1 ("What Is in Place") — it currently lists
   Bandit as an active control; it has not been providing coverage.

**Effort:** ~0.5 day for the Ruff `S`-rule rollout + triage; ~1 hour for the
CI/pre-commit guard.

---

### Finding 2 — HIGH — `mypy.ini` duplicate section + conftest collision breaks full-repo type check

**Where:** `mypy.ini:46-53`, root `conftest.py` vs `tests_bdd/conftest.py`.

**Evidence:**

```ini
[mypy-structlog]
ignore_missing_imports = True
...
[mypy-httpx]
ignore_missing_imports = True

[mypy-structlog]          # duplicate of lines 46-47
ignore_missing_imports = True
```

```
$ mypy .
mypy.ini: While reading from 'mypy.ini' [line 52]: section 'mypy-structlog' already exists
conftest.py: error: Duplicate module named "conftest" (also at "./tests_bdd/conftest.py")
Found 1 error in 1 file (errors prevented further checking)
```

CI never hits this because it invokes mypy pre-scoped
(`mypy core/ investor_app/finance/ ...`, `ci-quality.yml:184`), which never
resolves either `conftest.py` file. But that means **no one can run `mypy .`
or `mypy core/` (without the exact narrow CI path list) locally and get a
useful result** — any contributor or agent who reaches for the obvious
command hits a config error, not a type error, and may reasonably conclude
mypy is broken rather than investigate.

**Recommended fix:**

1. Delete the duplicate `[mypy-structlog]` block (`mypy.ini:52-53`) — trivial,
   zero-risk.
2. Resolve the conftest collision so `mypy .` is a valid command: either add
   `[mypy] exclude = ^tests_bdd/` (tests_bdd already has its own scoping
   needs — check whether it's meant to be type-checked at all), or add
   `explicit_package_bases = True` with `namespace_packages = True`, per
   mypy's own suggestion. Whichever direction, verify it doesn't change what
   CI actually checks — CI's explicit path list is unaffected either way,
   so this is a pure DX/correctness fix, not a CI risk.

**Effort:** ~1 hour, including verifying CI's scoped invocation is unaffected.

---

### Finding 3 — Open items already tracked in `SECURITY.md` (confirmed still open, one review-date risk)

`SECURITY.md` §4.2 already documents these accurately as of its last review
(2026-05-06); this audit re-confirms each is still unresolved in the current
tree and flags the review-date risk:

| ID | Severity | Summary | Location |
|---|---|---|---|
| GAP-06 | 🟠 HIGH | Redis has no auth in `docker-compose.yml` | `docker-compose.yml` |
| GAP-07 | 🟡 MEDIUM | No CSP header | templates / reverse proxy |
| GAP-08 | 🟡 MEDIUM | No CORS config (latent — no SPA yet) | `investor_app/settings.py` |
| GAP-09 | 🟡 MEDIUM | Postgres has no explicit strong password in compose | `docker-compose.yml` |
| GAP-10 | 🟡 MEDIUM | Anon throttle (100/hour) too permissive for calc endpoints | `investor_app/settings.py` |
| GAP-12 | 🟢 LOW | CI workflow has broad `contents: write` | `.github/workflows/*` |

**New in this audit:** `SECURITY.md`'s own policy says it must be reviewed
"quarterly (scheduled)"; **next scheduled review is 2026-08-06 — 10 days
from this audit.** GAP-06 (HIGH) predates that window and should not wait
for the quarterly cadence to be actioned.

**Recommended fix:** Fold GAP-06 through GAP-10 into this plan's Phase 1/2
(below) rather than waiting on the quarterly review; use the 2026-08-06
review to confirm closure and re-baseline, not to first triage them.

**Effort:** GAP-06 (Redis auth): ~2-3 hours including `.env.example` update
and compose changes. GAP-09 (Postgres password): ~1 hour, bundle with GAP-06
since both touch `docker-compose.yml`. GAP-10 (throttle class): ~1-2 hours.
GAP-07/08 (CSP/CORS): defer — both are explicitly conditional on features
not yet built (reverse-proxy hardening, SPA frontend); re-verify trigger
conditions at the 08-06 review rather than building speculatively.

---

### Finding 4 — LOW — Bare `pytest` invocation is a false-alarm generator

**Evidence:** Running `pytest -q` at the repo root (no `-k` filter) produces
`44 failed, 1842 passed, ... 4 errors`. Every failure is explained by missing
infrastructure the suite correctly expects to not have locally:

- `tests/acceptance/*` (18 failures) — by design, these hit a **live running
  server** via `httpx` (this was the Phase A rewrite documented in
  `docs/TOP_01_PLAN.md`); they're meant to run post-deployment, not against
  a cold checkout.
- `tests/test_docker_e2e.py` (4 errors) — requires a running Docker daemon.
- `core/tests/test_integration_attom.py::TestATTOMLiveIntegration` /
  `TestATTOMLiveEndpoints` (4 failures) — requires live ATTOM API credentials
  and network access.
- The remaining acceptance failures cascade from the same "no server running"
  root cause.

`make test` (→ `make test-unit`) and the CI `tests-unit` job both correctly
exclude these categories via `-k "not e2e and not docker and not integration
and not container and not startup and not add_to_pipeline and not
acceptance and not export and not unreachable_url"`. The gap is that this
exclusion lives only in the Makefile/CI YAML — a contributor or an
autonomous agent who types the obvious `pytest` at the repo root gets a
wall of red that looks like 44 broken things, not zero.

**Recommended fix:** Add a `pytest.ini`/`conftest.py` default marker-based
skip (or at minimum a root-level `README`/`AGENTS.md` one-liner: "never run
bare `pytest` — use `make test`") so the safe default matches what CI
actually gates on. A `pytest.ini` `addopts` default matching the Makefile's
`-k` expression is the more durable fix since it self-documents.

**Effort:** ~30 minutes.

---

### Finding 5 — LOW — Repo hygiene

- `test_check.db` (0 bytes) is tracked in git (`git ls-files` confirms) while
  `db.sqlite3`, `test_db.sqlite3`, and `.coverage` are correctly gitignored.
  Inconsistent; harmless but should be `git rm --cached test_check.db` and
  added to `.gitignore`.
- Root-level scratch/report files (`build-report.md`, `ci-diagnosis.md`,
  `ci-fix-report.md`, `review-report.md`, `verification-report.md`,
  `cross-validation-report.md`, `test-report.md`) are all correctly
  gitignored (confirmed via `git check-ignore -v`) — **no action needed**,
  flagged only so it's clear this was checked, not overlooked.

**Effort:** ~5 minutes.

---

### Non-findings (checked, no issue)

- `.env` is not tracked and is correctly gitignored, despite being open in
  the editor during this session.
- CI is green on `main` for the last 8 runs, including the nightly
  governance drift check and CodeQL.
- `ruff check .` and `ruff format --check .` both pass clean.
- No secrets found tracked in git via the ignore-list spot check.

## Implementation Plan

Phased by urgency, not by the size of the surrounding roadmap docs
(`docs/TOP_01_PLAN.md` already owns the multi-week reliability/observability
roadmap — this plan is scoped to what this audit found and does not
duplicate it).

### Phase 0 — Immediate (same day, <1 day total)

| # | Task | Finding | Effort |
|---|---|---|---|
| 0-1 | Remove duplicate `[mypy-structlog]` block in `mypy.ini` | 2 | 5 min |
| 0-2 | Fix conftest module collision so `mypy .` runs cleanly (scope decision: exclude `tests_bdd/` or add `explicit_package_bases`) | 2 | ~1 hr |
| 0-3 | Add Ruff `S` (flake8-bandit) rule set to `.ruff.toml`; triage initial findings; suppress accepted risks with `# noqa: S###` + comment | 1 | ~4 hrs |
| 0-4 | Add a "fail loudly on skipped files" guard around the existing bandit invocation in `ci-quality.yml`'s `lint` job and the pre-commit bandit hook | 1 | ~1 hr |
| 0-5 | Update `SECURITY.md` §4.1 to stop listing Bandit as providing active coverage until Finding 1 is resolved | 1 | 10 min |
| 0-6 | `git rm --cached test_check.db`; add to `.gitignore` | 5 | 5 min |

### Phase 1 — This week (before 2026-08-06 security review)

| # | Task | Finding | Effort |
|---|---|---|---|
| 1-1 | Add Redis password to `docker-compose.yml` + `.env.example` (GAP-06) | 3 | ~2-3 hrs |
| 1-2 | Add explicit strong Postgres password to `docker-compose.yml` + `.env.example` (GAP-09) | 3 | ~1 hr (bundle with 1-1) |
| 1-3 | Add `CalculationRateThrottle` (stricter anon rate) for `calculate_carrying_costs` and `compare_strategies` (GAP-10) | 3 | ~1-2 hrs |
| 1-4 | Add `pytest.ini` `addopts` (or equivalent) so bare `pytest` matches `make test-unit`'s safe default scope | 4 | ~30 min |
| 1-5 | File a tracking issue (or backlog entry) linking upstream `PyCQA/bandit#1219`, so Phase 0's Ruff stopgap has a defined exit condition | 1 | 15 min |

### Phase 2 — At the 2026-08-06 quarterly security review

| # | Task | Finding |
|---|---|---|
| 2-1 | Confirm Finding 1 (bandit) status: either upstream fixed and re-pinned, or Ruff `S` rules remain the system of record — update `SECURITY.md` §4.1 accordingly | 1 |
| 2-2 | Re-verify GAP-06/09/10 closure; move to "Resolved Limitations" | 3 |
| 2-3 | Re-assess GAP-07 (CSP) / GAP-08 (CORS) trigger conditions — still correctly deferred if no reverse-proxy hardening work or SPA frontend has started | 3 |
| 2-4 | Bump `SECURITY.md` "Last reviewed" / "Next scheduled review" dates | — |

### Explicitly out of scope for this plan

- `docs/TOP_01_PLAN.md` Phases B–D (financial-math verification suite,
  canary deployments, OpenTelemetry) — already planned, unaffected by this
  audit's findings, and far larger in scope.
- `docs/KNOWN_LIMITATIONS.md` entries (LIMIT-01 through LIMIT-19) — a
  separate, actively-maintained product-limitations list; nothing in this
  audit changes their status.
- GAP-07 (CSP) / GAP-08 (CORS) implementation — correctly gated on features
  not yet built; building them now would be speculative per this repo's own
  "don't build for hypothetical requirements" convention.

## Verification Checklist (for whoever picks up Phase 0/1)

- [ ] `mypy .` runs without config/collection errors (Finding 2)
- [ ] `ruff check .` still passes after enabling `S` rules, or all suppressions are reviewed and justified (Finding 1)
- [ ] Bandit (or its guard) fails the build if any file is skipped due to a scan exception (Finding 1)
- [ ] `docker compose up -d` still works end-to-end after Redis/Postgres password changes (Finding 3)
- [ ] Bare `pytest` at repo root exits 0 on a clean checkout with no live server/Docker/API creds (Finding 4)
- [ ] `git ls-files | grep test_check.db` returns nothing (Finding 5)

# Plan: Moving prei to Top 0.1%

> Written 2026-07-18 after 3-day CI/CD deep-fix session.
> Brutally honest. Nothing sugar-coated.

---

## Where We Are

We just spent 3 days fixing a CI pipeline that shipped to main broken. We renamed
curl assertions that check HTTP 200 to "smoke tests" and added 19 BDD scenarios
that use Django's TestClient inside a container and called it "acceptance testing."

We are not top 0.1%. We are not top 10%. We are in the middle of the pack —
better than most solo-founder projects, worse than any professional team that
takes reliability seriously.

---

## What Top 0.1% Means

Top 0.1% teams have:

| Trait | What it looks like |
|---|---|
| **Zero trust in green CI** | They don't celebrate passing tests. They treat a failing test as a bug in the test or the system. Every failure is investigated and root-caused within hours. |
| **Artifact is the unit of testing** | They never test source code. They test the deployed artifact. If a test passes against source but fails against the artifact, the test is wrong. |
| **Build-time dashboards** | Every build has a dashboard entry. Regressions are detected within one build cycle. A 2x build-time regression triggers an alert. |
| **Fully automated progressive delivery** | Code merged to main is deployed to canary within minutes. Canary is monitored for N minutes. If it passes, auto-promote to 100%. If it fails, auto-rollback. No human in the loop. |
| **Financial math is proven correct** | Every KPI function (NOI, cap rate, cash-on-cash, DSCR, IRR) has a test suite that enumerates edge cases and is validated against a reference implementation (Excel or a known-good library). |
| **SLOs with consequences** | They have published SLOs (99.9% availability, p99 latency < 200ms) and error budgets. When the error budget is exhausted, feature work stops. |
| **Documentation is a build artifact** | Docs are generated from code. API surface docs are tested for accuracy. Breaking doc changes fail CI. |

---

## Gap Assessment

### 🔴 Critical (less than top 50% — must fix)

| Gap | Current | Target |
|---|---|---|
| **Tests don't test the artifact** | BDD uses `django.test.Client` inside container — no HTTP, no real request/response cycle | All acceptance tests make real HTTP requests to the deployed artifact |
| **Smoke tests are status-code-only** | 9 curl checks assert HTTP 200 | Tests assert on content: JSON structure, HTML DOM, CSS rules |
| **No build-time monitoring** | Nobody knows if a build takes 5 min or 20 min | Dashboard with per-build metrics, regression alerting |
| **CI shipped broken to main** | The live-test job was broken for 3 commits before detection | No merge to main if CI on main is broken. Self-healing or rollback |
| **Documentation is stale** | API_SURFACE.md last updated 2026-05-20 | Docs generated from code, CI verifies accuracy |
| **No financial math verification suite** | 0 tests that prove NOI/cap-rate/DSCR are correct against a reference | Every KPI function has a parameterized test suite validated against a spreadsheet |

### 🟡 Serious (below top 25% — should fix)

| Gap | Current | Target |
|---|---|---|
| **No performance regression detection** | Lighthouse is informational (warn thresholds) | Error thresholds for CLS, FCP; build fails on regressions |
| **No SLOs** | No availability/latency targets defined | Published SLOs with error budgets |
| **No flaky test detection** | No mechanism to detect or quarantine flaky tests | Retry + quarantine system, flaky test dashboard |
| **Test coverage is superficial** | 70% line coverage but 0% on critical financial logic branches | 90%+ branch coverage on finance/ services |
| **No DAST beyond ZAP baseline** | ZAP baseline scan only | Full active ZAP scan against staging, auth-aware |
| **Docker image includes test code workaround** | `docker cp` test files into container | Either include tests in dev image, or write real HTTP tests |

### 🟢 Solid (above top 25% — maintain)

| Area | Status |
|---|---|
| Pre-commit hooks (ruff, mypy, bandit, gitleaks) | ✅ Above average |
| PR quality gates (lint, typecheck, unit, integration, e2e, coverage) | ✅ Good |
| Container smoke + BDD tests in CI | ✅ Working |
| Post-deployment acceptance pipeline | ✅ Phase 3 delivered today |
| Single-platform build (no unnecessary arm64) | ✅ Fixed |
| Build cache (gha cache) | ✅ Active |
| Test pyramid plan documented | ✅ Done |

---

## Implementation Phases

### Phase A: Foundation (now — 2 weeks)

**Goal:** Stop shipping broken CI, fix the artifact-testing gap, establish a baseline.

| # | Task | Impact | Effort |
|---|---|---|---|
| A-1 | Add self-test for CI on main: if the live-test job fails on main, block all PR merges | Prevents future main-breakage | 2-3 commits |
| A-2 | Rewrite BDD tests to use `httpx` instead of `django.test.Client` — test the running HTTP server, not the code inside it | The single biggest quality improvement available today | 5-8 commits |
| A-3 | Add `make test-acceptance` to CI quality gates so acceptance tests run on every PR | Catches regressions before merge | 1 commit |
| A-4 | Create a build-time log in CI and fail if build exceeds 10 min | Prevents build-time regressions | 1 commit |
| A-5 | Pin all acceptance test assertions to specific response shapes using Pydantic models | Turns "key exists" tests into full schema validation | 2-3 commits |

### Phase B: Financial Math (weeks 3-4)

**Goal:** Prove every KPI calculation is correct. This is existential for a real estate investment platform.

| # | Task | Impact | Effort |
|---|---|---|---|
| B-1 | Create a reference spreadsheet (or Python reference implementation) for all KPI functions: NOI, cap rate, cash-on-cash, DSCR, IRR, one_percent_rule, GRM | Establishes ground truth | 1-2 days |
| B-2 | Write parameterized property tests for each KPI function — 50+ edge cases per function (zero values, negative values, extreme values, currency precision boundaries) | Prevents financial calculation errors reaching users | 5-8 commits |
| B-3 | Add a CI gate that runs the financial math suite against the reference implementation and fails on any deviation | Makes math regressions impossible to ship | 1 commit |
| B-4 | Document every formula with its mathematical derivation in the docstring | Auditable, reviewable, trustable | 1-2 commits |

### Phase C: Deployment Reliability (weeks 5-6)

**Goal:** Deploy with confidence. Auto-rollback on any failure. Progressive delivery.

| # | Task | Impact | Effort |
|---|---|---|---|
| C-1 | Implement canary deployment: deploy to N% of traffic, monitor for M minutes, auto-promote or auto-rollback | Eliminates "deploy and pray" | 5-10 commits (infra-dependent) |
| C-2 | Add full OWASP ZAP active scan (not just baseline) against staging — auth-aware, spider-enabled | Catches injection, XSS, CSRF, auth bypass | 2-3 commits |
| C-3 | Create SLO dashboard: availability, p50/p95/p99 latency, error rate, deploy frequency | Makes reliability measurable | 3-5 commits |
| C-4 | Add flaky test detection: retry failed tests once, quarantine flaky tests after N failures, dashboard of flaky tests | Eliminates "rerun CI" culture | 3-5 commits |

### Phase D: Observability (weeks 7-8)

**Goal:** Know what's happening in production. Alert before users notice.

| # | Task | Impact | Effort |
|---|---|---|---|
| D-1 | Add structured JSON logging (structlog or python-json-logger) to all services and views | Makes log analysis possible | 2-3 commits |
| D-2 | Add OpenTelemetry tracing to HTTP handlers | Makes latency debugging possible | 2-3 commits |
| D-3 | Create alerting thresholds: p99 latency > 500ms, error rate > 1%, deploy failure rate > 10% | Catches degradation before users report it | 1-2 commits |
| D-4 | Auto-generate API surface docs from code annotations and fail CI if they're out of date | Documentation that doesn't lie | 2-3 commits |

---

## Honest Assessment

### What Makes This Hard

1. **This is a solo project.** Top 0.1% teams have dedicated SREs, QA engineers, and platform engineers. You're doing all of this alone. The fact that you have pre-commit hooks, CI gates, container testing, and a documented plan already puts you ahead of most solo projects.

2. **Financial math correctness is the hardest part.** The difference between a bug in CSS rendering and a bug in IRR calculation is that one looks bad and the other costs real money. You need formal verification of every KPI formula, and that requires mathematical rigor that most software engineers don't have.

3. **Canary deployments need infrastructure you don't have.** Progressive delivery requires at least 2 replicas, a load balancer, and traffic routing. On Render or a single-VPS setup, this isn't feasible without architectural changes.

4. **Build-time monitoring requires discipline you haven't established yet.** You just fixed a 3-day broken main pipeline. Before you can have build-time regression alerts, you need a culture where green CI is non-negotiable.

### What You Can Ship Next Week

If I had to pick the 3 highest-impact, lowest-effort things:

1. **Rewrite BDD tests to use `httpx` instead of `django.test.Client`.** This is the single biggest quality improvement available. It turns 19 scenarios that test Python code into 19 scenarios that test the actual deployed application through HTTP. Every CI run that passes after this change means the application actually works for a user.

2. **Add a build-time guard to CI.** If the live-test job on main is red, block all PR merges. This prevents the exact scenario we just spent 3 days fixing.

3. **Write the financial math verification suite.** Start with NOI and cap rate — the two most critical calculations. Parameterize 50 test cases per function. Validate against a spreadsheet. This is the only thing that separates a toy project from a real investment tool.

### What You Can't Ship Yet

- **Canary deployments** — need infrastructure you don't have
- **SLO dashboards** — need monitoring infrastructure
- **Automatic rollback** — already exists in post-deployment.yml, needs canary to be useful
- **Full DAST scanning** — ZAP active scan is Phase C, baseline is Phase A

---

## The One Honest Truth

If someone asked me "should I trust prei with real money decisions?" my answer today would be **no** — but after Phase A and Phase B, my answer would be **yes, with the understanding that it's a tool to inform decisions, not make them.**

The gap between "tool to inform" and "tool that decides" is exactly the gap between where you are and top 0.1%. That gap is filled with: exhaustive financial math verification, SLO-based progressive delivery, automated canary rollback, and real-user-journey acceptance tests.

You're closer than 99% of solo projects. You're farther than 100% of production-grade financial systems. The plan above closes that gap.

# Test Pyramid Implementation Plan

## Current State

```
PR Merge Gate (ci-quality.yml)
├── Typecheck + Lint
├── Unit tests (1308)
├── Integration tests
├── Container smoke test (9 curl assertions) ← misnamed "live acceptance"
├── BDD tests (standalone, not against container)
├── E2E Playwright tests (standalone, not against container)
└── Coverage ≥ 70%

Post-Deployment (post-deployment.yml)
└── 3 curl smoke tests against DEPLOY_URL

Production
└── Nothing automated
```

**Gap:** No test exercises the actual Docker image through real user workflows before merge.

---

## Phase 1: Rename & Clarify (immediate)

| What | From | To |
|---|---|---|
| Job name | `🧪 Tier 2 — Live Acceptance Test` | `🧪 Tier 2 — Smoke Test` |
| Section header | `=== Live Acceptance Tests ===` | `=== Smoke Tests ===` |
| Success message | `All live acceptance tests passed` | `All smoke tests passed` |

The 9 curl assertions are **smoke tests** — they prove the container boots and serves HTTP, nothing more. Renaming sets accurate expectations for what comes next.

---

## Phase 2: PR Gate — Run BDD + E2E Against the Container

**Goal:** Before merge, validate that the actual Docker image passes real user workflows.

### Changes to `docker-publish.yml` (live-test job)

After the health check passes and before cleanup:

```yaml
- name: Seed test data
  run: |
    docker exec prei-live-test python manage.py seed_data

- name: Run BDD acceptance tests against container
  env:
    BASE_URL: http://localhost:8000
  run: |
    docker exec -e DJANGO_SETTINGS_MODULE=investor_app.settings_test \
      prei-live-test pytest tests_bdd/ \
      --base-url=$BASE_URL \
      -q --tb=short

- name: Run Playwright E2E tests against container
  env:
    BASE_URL: http://localhost:8000
  run: |
    # Playwright needs a browser — install on the runner, point at container
    npx playwright install chromium
    pytest tests/e2e/ \
      --base-url=$BASE_URL \
      --headed=false \
      -q --tb=short
```

### Requirements

1. **`docker exec` needs the container running** — already guaranteed by the health check wait loop.
2. **Playwright browser install** — adds ~30s to the job. Can be cached.
3. **Test data** — `seed_data` must run to create demo properties. Currently skipped with `SKIP_SEED=1`. Need to remove that flag for this step (or run seed separately via `docker exec`).
4. **Database** — Must persist across the smoke test + BDD/E2E run. Currently `--rm` was removed in the previous fix, so the container stays alive. Good.

### CI Dependency Change

```
build-image
  ├── scan-image
  ├── live-test (smoke → smoke + bdd + e2e)
  │     └── needs no additional permissions
  └── publish
        └── needs: [build-image, scan-image]
              ↑ no longer needs live-test — publish can happen in parallel
```

Currently `publish` does NOT depend on `live-test`, so the container tests are non-blocking for publishing. That's fine — keep it that way for speed. But `gitops-deploy` depends on `[publish, live-test, scan-image]` so deploy still waits for all tests.

---

## Phase 3: Post-Deployment — Full Acceptance Against Staging

**Goal:** After GitOps syncs to staging/preview, run the full battery against the live URL.

### Changes to `post-deployment.yml`

Current state: runs 3 curl smokes against `DEPLOY_URL`.

Target:

```yaml
jobs:
  smoke:
    name: "🧪 Smoke Tests"
    # ...existing curl smokes...

  acceptance:
    name: "🧪 Acceptance Tests"
    needs: smoke
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - name: Run BDD tests against staging
        env:
          BASE_URL: ${{ needs.smoke.outputs.url }}
        run: |
          pip install -r requirements.txt
          pytest tests_bdd/ --base-url=$BASE_URL -q --tb=short

  performance:
    name: "📈 Performance Smoke"
    needs: smoke
    runs-on: ubuntu-latest
    steps:
      - name: Lighthouse CI
        uses: treosh/lighthouse-ci-action@v12
        with:
          urls: |
            ${{ needs.smoke.outputs.url }}/health/
            ${{ needs.smoke.outputs.url }}/discovery/
          uploadArtifacts: true
          temporaryPublicStorage: true

  rollback:
    name: "🔄 Rollback on Failure"
    needs: [smoke, acceptance, performance]
    if: failure() && vars.GITOPS_REPO != ''
    # ...existing rollback logic...
```

### Performance Smoke — What to Measure

| Metric | Target | Tool |
|---|---|---|
| Time to First Byte (TTFB) | < 200ms | Lighthouse |
| Largest Contentful Paint (LCP) | < 2.5s | Lighthouse |
| API response time (health) | < 500ms | curl + time |
| Database migration time | < 30s | measured in CI |

---

## Phase 4: Production — Canary + Synthetic Monitoring

**Goal:** After production deploy, validate with real traffic and catch regressions before users do.

### Component 1: Canary Deployment

GitOps pattern: deploy to a canary namespace/workload first, route a percentage of traffic, validate, then roll out fully.

```yaml
# Separate workflow: canary-deploy.yml (triggered by GitOps sync)
jobs:
  canary:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy canary
        run: |
          # Scale up canary replicas, shift 5% traffic
          kubectl set image deployment/prei-canary app=$NEW_IMAGE
          kubectl scale deployment/prei-canary --replicas=1

      - name: Validate canary (5 min window)
        run: |
          # Automated validation against canary URL
          pytest tests/canary/ --base-url=$CANARY_URL -q

      - name: Promote if healthy
        if: success()
        run: |
          kubectl set image deployment/prei-production app=$NEW_IMAGE
          kubectl scale deployment/prei-canary --replicas=0
```

**Current blocker:** This project doesn't deploy to Kubernetes yet (Django + SQLite on Render/similar). Canary requires at least 2 replicas and a load balancer. Defer until the platform supports it.

### Component 2: Synthetic Monitoring

Run periodic checks against production from an external service (or GitHub cron):

```yaml
# .github/workflows/synthetic-monitoring.yml
on:
  schedule:
    - cron: "*/5 * * * *"  # every 5 minutes

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - name: Health check
        run: |
          curl -sf --max-time 10 $DEPLOY_URL/health/ | \
            python3 -c "import sys,json; d=json.load(sys.stdin); assert d['status']=='ok'"

      - name: Critical user journey
        run: |
          # Login → search → view report
          npx playwright test tests/synthetic/ --base-url=$DEPLOY_URL

      - name: Notify on failure
        if: failure()
        uses: slackapi/slack-github-action@v2
        with:
          webhook: ${{ secrets.SLACK_WEBHOOK }}
```

### Component 3: Lighthouse Budget

Add a Lighthouse budget to prevent performance regressions:

```json
// lighthouserc.json
{
  "ci": {
    "assert": {
      "assertions": {
        "first-contentful-paint": ["error", {"maxNumericValue": 3000}],
        "largest-contentful-paint": ["error", {"maxNumericValue": 4000}],
        "cumulative-layout-shift": ["error", {"maxNumericValue": 0.1}],
        "interactive": ["error", {"maxNumericValue": 5000}]
      }
    },
    "upload": {
      "target": "temporary-public-storage"
    }
  }
}
```

---

## Dependency Graph

```
Phase 1 ─── Rename smoke tests (1 commit)
  │
Phase 2 ─── Run BDD/E2E against container (3-5 commits)
  │          ├── Seed data in live-test
  │          ├── Add BDD run step
  │          └── Add Playwright run step
  │
Phase 3 ─── Post-deployment acceptance + performance (3-5 commits)
  │          ├── Extract smoke URL as job output
  │          ├── Add acceptance job
  │          └── Add performance/lighthouse job
  │
Phase 4 ─── Production monitoring (ongoing, infra-dependent)
             ├── Canary deployment (requires K8s)
             ├── Synthetic monitoring cron
             └── Lighthouse budget
```

---

## Effort Estimate

| Phase | Complexity | Files Changed | Estimated Commits |
|---|---|---|---|
| 1 — Rename | Trivial | 1 | 1 |
| 2 — Container BDD/E2E | Medium | 2-3 | 3-5 |
| 3 — Post-deployment suite | Medium | 2 | 3-5 |
| 4 — Production monitoring | Medium-High (infra dependent) | 3-4 | 5-8 |

## Rollback Safety

Every phase is independently deployable. No phase breaks existing functionality — it only adds new test gates. If a new gate fails, existing workflows (smoke, unit, lint) still pass; only the new gate needs fixing before it becomes required.

# Test Pyramid Implementation Plan

## Current State

```
PR Merge Gate (ci-quality.yml)
├── Typecheck + Lint
├── Unit tests (1308)
├── Integration tests
├── Coverage ≥ 70%

Tier 2 Build & Publish (docker-publish.yml)
├── Container smoke test (9 curls)             ← renamed from "live acceptance"
├── BDD acceptance tests (19 scenarios)        ← runs INSIDE container via docker exec
├── E2E Playwright tests (standalone)          ← still separate, not yet against container

Post-Deployment (post-deployment.yml)
└── 3 curl smoke tests against DEPLOY_URL

Production
└── Nothing automated
```

**Gap:** BDD tests run inside the container (testing the image's Python environment) but still use Django's test client (not HTTP). True HTTP-level E2E is the next step.

---

## Phase 1: Rename & Clarify ✅

| What | From | To |
|---|---|---|
| Job name | `🧪 Tier 2 — Live Acceptance Test` | `🧪 Tier 2 — Smoke + BDD` |
| Section header | `=== Live Acceptance Tests ===` | `=== Smoke Tests ===` |
| Success message | `All live acceptance tests passed` | `All smoke tests passed` |

The 9 curl assertions are **smoke tests** — they prove the container boots and serves HTTP, nothing more.

---

## Phase 2: PR Gate — Run BDD Against the Container ✅

**Status:** Implemented. 19 BDD scenarios run inside the container via `docker exec` after smoke tests pass.

### How It Works (docker-publish.yml live-test job)

```
Start container (fast boot: skip_seed, skip_collectstatic)
  → Wait for healthy (up to 180s)
  → 9 smoke curls
  → Seed demo data (docker exec)
  → Collect static files (docker exec)
  → Copy tests_bdd/ into container
  → Run pytest tests_bdd/ (docker exec, 19 scenarios)
  → Cleanup (always)
```

### How to Run Locally

```bash
# 1. Build the image
docker build -t prei-test:local .

# 2. Start the container
docker run -d \
  --name prei-live-test \
  -p 8000:8000 \
  -e SECRET_KEY=local-dev-key \
  -e DJANGO_ENV=development \
  -e DEBUG=True \
  -e ALLOWED_HOSTS=localhost,127.0.0.1 \
  -e DATABASE_URL=sqlite:////tmp/live_test.db \
  -e RUN_MIGRATIONS=1 \
  -e SKIP_SEED=1 \
  -e SKIP_COLLECTSTATIC=1 \
  prei-test:local

# 3. Wait for healthy
sleep 10
curl http://localhost:8000/health/

# 4. Run smoke tests
echo -n "Health: "; curl -sf http://localhost:8000/health/ | python3 -m json.tool | grep -q '"status": "ok"' && echo "PASS" || echo "FAIL"
echo -n "Login: "; curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/accounts/login/; echo ""

# 5. Seed data + collect static
docker exec prei-live-test python manage.py seed_data
docker exec prei-live-test python manage.py collectstatic --noinput

# 6. Copy tests and run BDD
find tests_bdd -path '*/__pycache__/*' -delete 2>/dev/null; find tests_bdd -name '*.pyc' -delete 2>/dev/null
docker exec prei-live-test rm -rf /app/tests_bdd 2>/dev/null || true
docker cp tests_bdd prei-live-test:/app/tests_bdd
docker exec \
  -e DJANGO_SETTINGS_MODULE=investor_app.settings_test \
  prei-live-test \
  python -m pytest tests_bdd/ -q --tb=short

# 7. Clean up
docker stop prei-live-test
docker rm prei-live-test
```

### Requirements

1. **Docker** installed and running
2. **`prei-test:local`** image built (or pull from GHCR)
3. **No other process on port 8000** (or change the port mapping)
4. **`make smoke`** target also works for quick curl checks (does not run BDD tests)

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

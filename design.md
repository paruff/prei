# Design: Post-Deployment Acceptance Pipeline
# Written: 2026-07-18 session with paruff
# Status: Draft for feature-flow implementation

---

## 1. Architecture Overview

### 1.1 Current vs Target

```
CURRENT:

push to main → docker-publish.yml (build + smoke + BDD) → deploy
                                                           ↓
                                           post-deployment.yml
                                           └─ 3 curl HTTP 200 checks
                                           └─ rollback (unused)

TARGET:

push to main → docker-publish.yml (build + smoke + BDD) → deploy
                                                           ↓
                                           post-deployment.yml
                                           ├─ smoke (3 curl checks, fast)
                                           ├─ acceptance (HTTP content tests)
                                           ├─ performance (Lighthouse budgets)
                                           ├─ security (OWASP ZAP baseline)
                                           └─ rollback (auto on any failure)
```

### 1.2 Job Dependency Graph

```
smoke
  ├── acceptance (needs: smoke)
  ├── performance (needs: smoke)
  └── security (needs: smoke)
        │
        └── rollback (needs: [smoke, acceptance, performance, security], if: failure())
```

---

## 2. Component Design

### 2.1 Acceptance Tests (`tests/acceptance/`)

**Location:** `tests/acceptance/test_deployment.py`

**Tech stack:** `httpx` for HTTP requests, `pytest` for runner, `pydantic` for response validation

**Test structure:**

```
tests/acceptance/
├── __init__.py
├── conftest.py           ← base_url fixture, client fixture
├── test_health.py        ← AC-01, AC-08
├── test_pages.py         ← AC-02, AC-06, AC-07
├── test_api.py           ← AC-03, AC-04, AC-05
└── Makefile target: test-acceptance
```

**Key design decisions:**
- Use `httpx` (already in requirements.txt) for HTTP client
- Tests run from CI runner against deployment URL (NOT inside container)
- `BASE_URL` configured via environment variable
- Assert on JSON shape using Python dict access, not string matching
- Assert on HTML content using `lxml.html` or `beautifulsoup4` (already installed)

### 2.2 Performance Tests

**Tool:** `treosh/lighthouse-ci-action@v12`

**Config:** `lighthouserc.json` at repo root

```json
{
  "ci": {
    "assert": {
      "assertions": {
        "first-contentful-paint": ["error", {"maxNumericValue": 3000}],
        "largest-contentful-paint": ["error", {"maxNumericValue": 4000}],
        "cumulative-layout-shift": ["error", {"maxNumericValue": 0.1}],
        "interactive": ["error", {"maxNumericValue": 5000}],
        "server-response-time": ["error", {"maxNumericValue": 1000}]
      }
    },
    "upload": {
      "target": "temporary-public-storage"
    }
  }
}
```

**URLs to test:**
- `{DEPLOY_URL}/health/` — lightweight endpoint
- `{DEPLOY_URL}/discovery/` — typical page load

### 2.3 Security Tests

**Tool:** `zaproxy/action-baseline@v1` (OWASP ZAP baseline scan)

**Config:** Scans the deployment URL for common web vulnerabilities.

**Scope:**
- Passive scanning only (no active attacks against production)
- Alerts classified as HIGH or CRITICAL cause failure
- MEDIUM and LOW are logged but don't fail

### 2.4 Smoke Tests (keep existing)

The existing 3 curl checks are kept as fast pre-flight. They run first and fail fast if the deployment isn't responding at all.

---

## 3. Workflow Changes (`post-deployment.yml`)

### 3.1 Job: `smoke` (existing, minor updates)

Keep the existing 3 curl checks. Output the deployment URL for downstream jobs.

### 3.2 Job: `acceptance` (new)

```yaml
acceptance:
  name: "🧪 Acceptance Tests"
  needs: smoke
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v7
    - uses: ./.github/actions/python-setup
    - name: Install dependencies
      run: pip install -r requirements.txt httpx
    - name: Run acceptance tests
      env:
        BASE_URL: ${{ needs.smoke.outputs.target }}
      run: |
        python -m pytest tests/acceptance/ -q --tb=short -v
```

### 3.3 Job: `performance` (new)

```yaml
performance:
  name: "📈 Performance"
  needs: smoke
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v7
    - name: Lighthouse CI
      uses: treosh/lighthouse-ci-action@v12
      with:
        urls: |
          ${{ needs.smoke.outputs.target }}/health/
          ${{ needs.smoke.outputs.target }}/discovery/
        configPath: ./lighthouserc.json
        uploadArtifacts: true
        temporaryPublicStorage: true
```

### 3.4 Job: `security` (new)

```yaml
security:
  name: "🛡️ Security Scan"
  needs: smoke
  runs-on: ubuntu-latest
  steps:
    - name: OWASP ZAP Baseline
      uses: zaproxy/action-baseline@v1
      with:
        target: ${{ needs.smoke.outputs.target }}
        allow_issue_writing: false
        fail_action: true
        cmd_options: "-I"  # passive scan only
```

### 3.5 Job: `rollback` (existing, updated trigger)

Update the `if` condition to check all upstream jobs, not just `smoke`.

---

## 4. Local Development

### 4.1 Running Acceptance Tests Locally

```bash
# Start container (see TEST_PYRAMID_PLAN.md for full instructions)
docker run -d --name prei-local-test -p 8000:8000 ... prei-test:local

# Run acceptance tests against local container
BASE_URL=http://localhost:8000 python -m pytest tests/acceptance/ -v

# Clean up
docker stop prei-local-test && docker rm prei-local-test
```

### 4.2 Makefile Target

```makefile
test-acceptance:
	@echo "Running acceptance tests against \$${BASE_URL:-http://localhost:8000}"
	BASE_URL=$${BASE_URL:-http://localhost:8000} python -m pytest tests/acceptance/ -q --tb=short
```

---

## 5. Constraints & Risks

| Risk | Mitigation |
|---|---|
| OWASP ZAP baseline may generate false positives | Use `fail_action: true` only for HIGH/CRITICAL; review weekly |
| Lighthouse CI requires Node.js | Runner has Node.js pre-installed |
| Tests depend on deployed URL being reachable | Smoke job runs first as gate |
| httpx not in production requirements | Already in requirements.txt (line 40) |
| Security scan may timeout on slow pages | ZAP baseline has internal timeout; scan single URL |

# Design: Phase C — Deployment Reliability
# Written: 2026-07-18
# Status: Draft

---

## 1. Architecture

### C-2: Full OWASP ZAP Active Scan

Update `post-deployment.yml` security job to use active scanning:

```yaml
security:
  name: "🛡️ Security Scan"
  needs: smoke
  runs-on: ubuntu-latest
  steps:
    - name: OWASP ZAP Full Scan
      uses: zaproxy/action-full-scan@v1
      with:
        target: ${{ needs.smoke.outputs.target }}
        allow_issue_writing: false
        fail_action: true
        rules_file_name: ".zap/rules.tsv"
        cmd_options: "-a -j"  # active scan + auth
```

Configuration file: `.zap/rules.tsv` with severity thresholds.

### C-3: SLO Dashboard

A script at `scripts/slo-report.sh` that computes:

```
Deploy Frequency (30d):   12 deployments
Change Failure Rate:       8.3% (1 failure / 12 deploys)
Mean Time to Recovery:     5 min
Last Deploy:              2026-07-18 14:00 UTC
```

Uses GitHub API to count successful vs failed workflow runs.

### C-4: Flaky Test Detection

1. Add `pytest-rerunfailures` to `requirements.txt` and `pytest.ini`
2. Update CI unit test command to include `--reruns 1 --reruns-delay 5`
3. Add `.flake-reports/` directory for flaky test tracking
4. Add a quarantine step that checks `.flake-reports/` for tests failing ≥3 times

```ini
# pytest.ini
addopts = --reruns 1 --reruns-delay 5
```

### C-1: Canary Deployment Plan

Document `docs/DEPLOYMENT_STRATEGY.md` describing the future canary architecture:

```
traffic splitter
  ├── 95% → stable replica (current image)
  └──  5% → canary replica (new image)
          → monitor for 5 min
          → if healthy: promote to 100%
          → if unhealthy: rollback
```

---

## 2. File Changes

| File | Change | Purpose |
|---|---|---|
| `post-deployment.yml` | Update security job to full scan | C-2 |
| `.zap/rules.tsv` | New: ZAP severity rules | C-2 |
| `pytest.ini` | Add --reruns args | C-4 |
| `requirements.txt` | Add pytest-rerunfailures | C-4 |
| `ci-quality.yml` | Update unit test command with --reruns | C-4 |
| `scripts/slo-report.sh` | New: SLO computation script | C-3 |
| `docs/DEPLOYMENT_STRATEGY.md` | New: Canary plan | C-1 |
| `Makefile` | Add test-slos target | C-3 |

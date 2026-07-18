# Design: GitOps Phase 2 — uFawkesObs Integration
# Written: 2026-07-18
# Status: Draft

---

## 1. Architecture

```
prei repo (this repo)
  ├── docker-publish.yml → build + publish + deploy
  ├── post-deployment.yml → smoke + acceptance + security + rollback
  │   └── NEW: deploy-notify step → POST to uFawkesObs webhook
  ├── scripts/dora-metrics.sh → output DORA metrics as JSON
  └── docs/UFAWKES_OBS_SETUP.md → integration guide

uFawkesObs (separate service)
  ├── monitors prei repo via webhook events
  ├── collects DORA metrics from GH API + webhook data
  └── exposes dashboard at ufawkes.dev
```

## 2. Webhook Integration

Add a `deploy-notify` step to `post-deployment.yml`:

```yaml
- name: Notify uFawkesObs
  if: vars.UFAWKES_WEBHOOK_URL != ''
  run: |
    curl -sf -X POST "$UFAWKES_WEBHOOK_URL" \
      -H "Content-Type: application/json" \
      -d "{
        \"event\": \"deploy-complete\",
        \"repo\": \"${{ github.repository }}\",
        \"sha\": \"${{ github.sha }}\",
        \"status\": \"${{ job.status }}\",
        \"url\": \"${{ needs.smoke.outputs.target }}\"
      }"
```

## 3. DORA Metrics Script

`scripts/dora-metrics.sh` queries GitHub API for:
- Deploy frequency: count of successful `docker-publish.yml` runs in last 30 days
- Lead time: time from first commit to deploy (approximated from PR merge → deploy)
- Change failure rate: failed deploys / total deploys
- MTTR: mean time from failure to next successful deploy

Outputs JSON consumable by uFawkesObs dashboard.

## 4. File Changes

| File | Change | Purpose |
|---|---|---|
| `docs/UFAWKES_OBS_SETUP.md` | New | Integration guide |
| `scripts/dora-metrics.sh` | New | DORA metrics JSON export |
| `.github/workflows/post-deployment.yml` | Modified | Add deploy-notify step |
| `Makefile` | Modified | Add `make dora-metrics` target |
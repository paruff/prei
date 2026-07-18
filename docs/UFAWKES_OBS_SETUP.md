# uFawkesObs Integration Guide — prei

> uFawkesObs is a GitOps-native observability platform that collects DORA metrics
> from GitHub Actions workflows and deployment manifests. This guide documents the
> integration between prei and uFawkesObs.

---

## Prerequisites

| Requirement | Status |
|---|---|
| uFawkesObs deployed and running | Required |
| `GITOPS_REPO` variable set in prei GitHub | Required |
| `GITOPS_DEPLOY_KEY` with write access | Required |
| `deploy/overlays/production/docker-compose.override.yml` | ✅ Created (Phase 1) |
| GitOps pipeline runs on `main` | ✅ `docker-publish.yml` |
| Post-deployment smoke/acceptance/security | ✅ `post-deployment.yml` |

---

## Step 1: Configure GitHub Variables

In prei's GitHub repo → Settings → Secrets and variables → Variables:

| Variable | Value | Purpose |
|---|---|---|
| `GITOPS_REPO` | `paruff/prei` | Git repo containing deployment manifests |
| `GITOPS_DEPLOY_KEY` | (generated deploy key) | Write access to manifest repo |
| `UFAWKES_WEBHOOK_URL` | `https://ufawkes.dev/api/webhook/deploy` | uFawkesObs deploy event endpoint |

---

## Step 2: Register uFawkesObs Webhook

The `post-deployment.yml` workflow posts deploy events to uFawkesObs. Once the
`UFAWKES_WEBHOOK_URL` variable is set, every deployment will be tracked:

```
post-deployment.yml
  ├── smoke → acceptance → performance → security
  ├── deploy-notify: POST to uFawkesObs with deploy status
  └── rollback
```

uFawkesObs receives:
```json
{
  "event": "deploy-complete",
  "repo": "paruff/prei",
  "sha": "abc123...",
  "status": "success|failure",
  "url": "https://prei.example.com"
}
```

---

## Step 3: Validate DORA Metrics

uFawkesObs computes DORA metrics from the prei repo's CI history:

| Metric | Source | Target |
|---|---|---|
| Deploy Frequency | `docker-publish.yml` successful runs | ≥ 1/day |
| Lead Time for Changes | Time from PR merge to deploy | < 1 hour |
| Change Failure Rate | Failed deploys / total deploys | < 15% |
| Mean Time to Recovery | Time from failure to next success | < 10 min |

To verify locally before connecting to uFawkesObs:

```bash
make dora-metrics
```

This runs `scripts/dora-metrics.sh` which outputs the current DORA metrics as JSON.

---

## Step 4: Dashboard Access

Once uFawkesObs is connected, the prei dashboard is available at:

```
https://ufawkes.dev/dashboard/prei
```

The dashboard shows:
- Deployment frequency over time (bar chart)
- Change failure rate (gauge)
- Lead time distribution (histogram)
- MTTR trend (line chart)
- Recent deploy log with status and links

---

## Troubleshooting

| Problem | Check |
|---|---|
| Webhook not receiving events | Verify `UFAWKES_WEBHOOK_URL` is set and reachable |
| No DORA metrics | Check that `docker-publish.yml` runs on `main` |
| Manifest not updating | Verify `GITOPS_DEPLOY_KEY` has write access to `GITOPS_REPO` |
| Dashboard shows no data | Check uFawkesObs logs for webhook processing errors |

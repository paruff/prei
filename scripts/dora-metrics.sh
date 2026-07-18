#!/usr/bin/env bash
# DORA metrics export — GitOps Phase 2 uFawkesObs integration.
# Outputs JSON consumable by uFawkesObs dashboard.

set -euo pipefail

DEPLOY_FREQUENCY=0
LEAD_TIME="N/A"
CHANGE_FAILURE_RATE=0
MTTR="N/A"

# Deploy frequency: count successful docker-publish.yml runs in last 30 days
if command -v gh &>/dev/null; then
  TOTAL=$(gh run list --branch main --workflow docker-publish.yml --limit 100 \
    --json conclusion --jq 'length' 2>/dev/null || echo 0)
  SUCCESS=$(gh run list --branch main --workflow docker-publish.yml --limit 100 \
    --json conclusion --jq '[.[] | select(.conclusion == "success")] | length' 2>/dev/null || echo 0)
  FAILED=$((TOTAL - SUCCESS))
  DEPLOY_FREQUENCY=$SUCCESS
  if [ "$TOTAL" -gt 0 ]; then
    CHANGE_FAILURE_RATE=$(awk "BEGIN {printf \"%.1f\", ${FAILED}/${TOTAL}*100}")
  fi
fi

cat <<EOF
{
  "repo": "${GITHUB_REPOSITORY:-paruff/prei}",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "metrics": {
    "deploy_frequency": ${DEPLOY_FREQUENCY},
    "lead_time": "${LEAD_TIME}",
    "change_failure_rate": ${CHANGE_FAILURE_RATE},
    "mttr": "${MTTR}"
  }
}
EOF

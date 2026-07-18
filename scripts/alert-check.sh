#!/usr/bin/env bash
# Alerting threshold check — Phase D Observability.
# Checks Tier 2 Governance deploy failure rate over the last 10 runs.
# Warns if > 10% failure rate.

set -euo pipefail

echo "=== Deploy Health Alert ==="

TOTAL=$(gh run list --branch main --workflow docker-publish.yml --limit 10 \
  --json conclusion --jq 'length' 2>/dev/null || echo 0)
FAILED=$(gh run list --branch main --workflow docker-publish.yml --limit 10 \
  --json conclusion --jq '[.[] | select(.conclusion == "failure")] | length' 2>/dev/null || echo 0)

if [ "$TOTAL" -eq 0 ]; then
  echo "No deployment runs found — skipping alert check."
  exit 0
fi

RATE=$(awk "BEGIN {printf \"%.1f\", ${FAILED}/${TOTAL}*100}")

echo "  Last 10 deploys: ${TOTAL}"
echo "  Failed:          ${FAILED}"
echo "  Failure rate:    ${RATE}%"

if awk "BEGIN {exit !($RATE > 10)}"; then
  echo "::warning::Deploy failure rate is ${RATE}% — exceeds 10% threshold"
fi

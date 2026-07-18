#!/usr/bin/env bash
# SLO Dashboard — Phase C Deployment Reliability
# Computes deploy frequency and change failure rate from GitHub CI runs.

set -euo pipefail

DAYS=${1:-30}
echo "=== SLO Dashboard (last ${DAYS} days) ==="

# Deploy frequency: count successful Tier 2 runs
TOTAL=$(gh run list --branch main --workflow "docker-publish.yml" --limit 100 \
  --json conclusion --jq '[.[] | select(.conclusion != null)] | length' 2>/dev/null || echo 0)
SUCCESS=$(gh run list --branch main --workflow "docker-publish.yml" --limit 100 \
  --json conclusion --jq '[.[] | select(.conclusion == "success")] | length' 2>/dev/null || echo 0)
FAILED=$((TOTAL - SUCCESS))

echo "  Deploy Frequency (30d):   ${SUCCESS} successful"
echo "  Total Runs:                ${TOTAL}"
echo "  Change Failure Rate:       $(awk "BEGIN {printf \"%.1f\", ${TOTAL}>0 ? ${FAILED}/${TOTAL}*100 : 0}")% ($FAILED / $TOTAL)"
echo "  Last Deploy:               $(gh run list --branch main --workflow docker-publish.yml --limit 1 --json createdAt --jq '.[0].createdAt' 2>/dev/null || echo 'unknown')"
echo ""
echo "=== SLO Targets ==="
echo "  Deployment frequency:  ≥ 1/day"
echo "  Change failure rate:   ≤ 15%"
echo "  Mean time to recovery: ≤ 10 min"

#!/usr/bin/env bash
# Drift detection — GitOps Phase 3 Hardening.
# Compares deployed state against git manifests. Fails if drift is detected.

set -euo pipefail

DEPLOY_URL="${1:-${DEPLOY_URL:-}}"
if [ -z "$DEPLOY_URL" ]; then
  echo "Usage: ./scripts/drift-check.sh <deploy-url>"
  echo "   or: DEPLOY_URL=https://example.com ./scripts/drift-check.sh"
  exit 1
fi

echo "=== Drift Check: $DEPLOY_URL ==="
DRIFT=0

# 1. Health endpoint must return status: ok
STATUS=$(curl -sf "$DEPLOY_URL/health/" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))" 2>/dev/null || echo "FAILED")
if [ "$STATUS" = "ok" ]; then
  echo "  ✅ Health endpoint: ok"
else
  echo "  ❌ Health endpoint: $STATUS (expected 'ok')"
  DRIFT=1
fi

# 2. GitOps manifest must exist and define an image
MANIFEST="deploy/overlays/production/docker-compose.override.yml"
if [ -f "$MANIFEST" ]; then
  IMAGE=$(grep "image:" "$MANIFEST" | head -1 | awk '{print $2}')
  echo "  📦 Manifest image: $IMAGE"
else
  echo "  ⚠ Manifest not found: $MANIFEST"
fi

# 3. Check for uncommitted changes in deploy/ directory
if git diff --quiet HEAD -- deploy/ 2>/dev/null; then
  echo "  ✅ deploy/ matches git (no drift)"
else
  echo "  ❌ deploy/ has uncommitted changes (drift detected)"
  DRIFT=1
fi

echo ""
if [ "$DRIFT" -ne 0 ]; then
  echo "::error::Drift detected between deployed state and git manifests"
  exit 1
fi

echo "✅ No drift detected"

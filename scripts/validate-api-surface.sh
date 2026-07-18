#!/usr/bin/env bash
# API Surface Validation — Phase D Observability.
# Checks that every function documented in docs/API_SURFACE.md still
# exists in the actual source code. Fails CI if a documented function
# has been removed or renamed.

set -euo pipefail

DOC="docs/API_SURFACE.md"
MISSING=0

echo "=== API Surface Validation ==="

# Extract documented function names from API_SURFACE.md
# Lines like: ### 'function_name' or ### `function_name(...)`
FUNCTIONS=$(grep -oP '### [`'"'"']?\K[a-z_]+(?=[`'"'"'(])' "$DOC" 2>/dev/null || true)

if [ -z "$FUNCTIONS" ]; then
  echo "No documented functions found in $DOC"
  exit 0
fi

for fn in $FUNCTIONS; do
  # Search source code for the function definition
  if ! grep -rq "def ${fn}(" core/ investor_app/finance/ 2>/dev/null; then
    echo "  ❌ MISSING: ${fn}() — documented but not found in source"
    MISSING=$((MISSING + 1))
  else
    echo "  ✅ ${fn}()"
  fi
done

echo ""
if [ "$MISSING" -gt 0 ]; then
  echo "::error::${MISSING} documented function(s) missing from source"
  exit 1
fi

echo "All documented functions found in source."

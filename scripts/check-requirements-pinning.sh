#!/usr/bin/env bash
# check-requirements-pinning.sh
# Check that all non-comment, non-comment lines in requirements.txt
# include a version constraint operator (>=, <=, ==, ~=, !=).
#
# Exit codes:
#   0 = all good (or file not found)
#   1 = one or more unpinned dependencies found
#
# Usage:
#   ./scripts/check-requirements-pinning.sh [path/to/requirements.txt]

set -euo pipefail

target="${1:-requirements.txt}"

if [ ! -f "$target" ]; then
  echo "::notice file=$target,title=check-requirements-pinning::File not found — skipping"
  exit 0
fi

# Find lines that are:
#   - not empty
#   - not comments (#)
#   - not -r include directives
#   - do NOT contain any version operator character (>= <= == ~= !=)
unpinned=$(grep -v '^\s*\(#\|$\)' "$target" \
           | grep -v '^\s*-r\s' \
           | { grep -v '[><=!~]' || true; })

if [ -n "$unpinned" ]; then
  echo "::error file=$target,title=check-requirements-pinning::Unpinned dependencies found"
  echo "The following entries lack a version constraint:"
  echo "$unpinned"
  exit 1
fi

echo "::notice file=$target,title=check-requirements-pinning::All dependencies pinned ✓"
exit 0

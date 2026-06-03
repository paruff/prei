#!/bin/sh
set -eu

SAVE=0
if [ "${1:-}" = "--save" ]; then
  SAVE=1
fi

ROOT_DIR=$(pwd)
FILES="AGENTS.md .github/copilot-instructions.md CLAUDE.md"
PRICE_PER_1K=0.003
WORK_DAYS=22
USAGE_LIGHT=10
USAGE_MODERATE=20
USAGE_HEAVY=50
LINE_TARGET=80
TOKEN_TARGET=320

calc_tokens() {
  # chars/4 rounded down, minimum 0
  chars="$1"
  echo $((chars / 4))
}

calc_cost() {
  tokens="$1"
  interactions_per_day="$2"
  interactions=$((interactions_per_day * WORK_DAYS))
  awk -v t="$tokens" -v i="$interactions" -v p="$PRICE_PER_1K" 'BEGIN { printf "%.4f", (t*i/1000.0)*p }'
}

total_lines=0
total_tokens=0

TMP_OUT="$(mktemp /tmp/token-audit.XXXXXX)"
trap 'rm -f "$TMP_OUT"' EXIT

{
  echo "# Token Audit Report"
  echo "Repository: $ROOT_DIR"
  echo ""
  echo "## Always-on context files"
  printf "%-40s %-8s %-10s\n" "File" "Lines" "Tokens"
  printf "%-40s %-8s %-10s\n" "----------------------------------------" "--------" "----------"

  for f in $FILES; do
    if [ -f "$f" ]; then
      lines=$(wc -l < "$f" | tr -d ' ')
      chars=$(wc -c < "$f" | tr -d ' ')
      tokens=$(calc_tokens "$chars")
      total_lines=$((total_lines + lines))
      total_tokens=$((total_tokens + tokens))
      printf "%-40s %-8s %-10s\n" "$f" "$lines" "$tokens"
    else
      printf "%-40s %-8s %-10s\n" "$f" "0" "0"
    fi
  done

  echo ""
  echo "Total always-on lines: $total_lines"
  echo "Total always-on tokens: $total_tokens"
  echo ""

  light_cost=$(calc_cost "$total_tokens" "$USAGE_LIGHT")
  moderate_cost=$(calc_cost "$total_tokens" "$USAGE_MODERATE")
  heavy_cost=$(calc_cost "$total_tokens" "$USAGE_HEAVY")

  echo "## Estimated monthly input-token cost (USD)"
  echo "- Light   (${USAGE_LIGHT}/day):   \$$light_cost"
  echo "- Moderate(${USAGE_MODERATE}/day): \$$moderate_cost"
  echo "- Heavy   (${USAGE_HEAVY}/day):   \$$heavy_cost"
  echo ""

  echo "## AGENTS.md lean target check"
  if [ -f "AGENTS.md" ]; then
    a_lines=$(wc -l < "AGENTS.md" | tr -d ' ')
    a_chars=$(wc -c < "AGENTS.md" | tr -d ' ')
    a_tokens=$(calc_tokens "$a_chars")
    status="LEAN"
    if [ "$a_lines" -gt "$LINE_TARGET" ] || [ "$a_tokens" -gt "$TOKEN_TARGET" ]; then
      status="OVER BUDGET"
    fi
    echo "- AGENTS.md lines: $a_lines (target <= $LINE_TARGET)"
    echo "- AGENTS.md tokens: $a_tokens (target <= $TOKEN_TARGET)"
    echo "- Status: $status"
  else
    echo "- AGENTS.md missing"
  fi
  echo ""

  echo "## .copilotignore check"
  if [ -f ".copilotignore" ]; then
    rule_count=$(grep -v '^[[:space:]]*$' .copilotignore | grep -vc '^[[:space:]]*#' || true)
    echo "- Present: yes"
    echo "- Rule count: $rule_count"
  else
    echo "- Present: no"
    echo "- Rule count: 0"
  fi
  echo ""

  echo "## Top 10 largest files (bytes)"
  find . -type f ! -path './.git/*' -print0 | xargs -0 wc -c 2>/dev/null | sort -nr | head -n 10
  echo ""

  echo "## Recommendations"
  if [ "$total_tokens" -gt 320 ]; then
    echo "- Reduce always-on context further; move more policy details into .github/skills/."
  else
    echo "- Always-on context is within lean target; keep policy details on-demand."
  fi
  echo "- Run this audit weekly and before major instruction updates."
  echo "- Prefer Ask/Edit mode before Agent mode for simple tasks to control burn rate."
} | tee "$TMP_OUT"

if [ "$SAVE" -eq 1 ]; then
  mkdir -p docs
  {
    echo ""
    echo "## Token Audit Snapshot $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    cat "$TMP_OUT"
  } >> docs/METRICS.md
  echo ""
  echo "Saved audit snapshot to docs/METRICS.md"
fi

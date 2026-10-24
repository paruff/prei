#!/usr/bin/env bash
# One-shot setup of the "Real Estate Investor" board (project #3) for the AGENTS.md "Workflow" section.
# Review, then run once from the repo root AFTER the intent/spec/plan PR merges:
#   bash scripts/setup-project-board.sh
# Needs gh logged in with the `project` scope (check: gh auth status).
# Safe to re-run: skips options, fields, milestones and issues that already exist (matched by exact title).
set -euo pipefail

OWNER=paruff
REPO=paruff/prei
P=3
BOARD="Real Estate Investor"
REL_A="Beta A: rent data and GACS"
REL_B="Beta B: crime data and background work"
REL_C="Beta C: security headers"

log() { echo "$*" >&2; }
url_of() { echo "https://github.com/$REPO/issues/$1"; }
set_field() { # <url> <field> <value>
  gh project item-edit "$P" --owner "$OWNER" --url "$1" --field "$2" --value "$3" >/dev/null
  log "  $2=$3 <- $1"
}
existing_url() { # <exact title>
  gh issue list --repo "$REPO" --state all --limit 1000 --json title,url \
    --template '{{range .}}{{.title}}{{"\t"}}{{.url}}{{"\n"}}{{end}}' |
    awk -F'\t' -v t="$1" '$1 == t { print $2; exit }'
}
new_issue() { # <title> <milestone> <status> <body> -> prints URL
  local url
  url=$(existing_url "$1")
  if [ -n "$url" ]; then
    log "  exists: $url"
    gh project item-add "$P" --owner "$OWNER" --url "$url" >/dev/null 2>&1 || true
  else
    url=$(gh issue create --repo "$REPO" --title "$1" --milestone "$2" --project "$BOARD" --body "$4")
  fi
  set_field "$url" Status "$3"
  echo "$url"
}

# --- 1. Status options -------------------------------------------------------
# Replacing single-select options through the API may clear existing values (uncertain), so snapshot
# every item's Status first and restore it afterwards. Old "Ready" -> "Ready for agent",
# "In review" -> "Needs human decision".
FIELD=$(gh project field-list "$P" --owner "$OWNER" --format json --jq '.fields[] | select(.name=="Status") | .id')
OPTS=$(gh project field-list "$P" --owner "$OWNER" --format json --jq '.fields[] | select(.name=="Status") | [.options[].name] | join("|")')
if [[ "$OPTS" == *"Ready for agent"* ]]; then
  log "Status options already set"
else
  SNAP=$(mktemp)
  gh project item-list "$P" --owner "$OWNER" --limit 500 --format json \
    --jq '.items[] | select(.status != null) | "\(.id)\t\(.status)"' >"$SNAP"
  log "Snapshot of $(wc -l <"$SNAP") item statuses: $SNAP"
  # shellcheck disable=SC2016  # $f is a GraphQL variable
  gh api graphql -f f="$FIELD" -f query='
mutation($f: ID!) {
  updateProjectV2Field(input: {fieldId: $f, singleSelectOptions: [
    {name: "Backlog",              color: GRAY,   description: "Not ready, or its release is not planned yet"},
    {name: "Ready for agent",      color: BLUE,   description: "Plan row, spec IDs and an Exit criterion present"},
    {name: "In progress",          color: YELLOW, description: "Claimed and being worked on"},
    {name: "Needs human decision", color: PURPLE, description: "Waiting on a person; Gate says which decision"},
    {name: "Blocked",              color: RED,    description: "Waiting on something named in a comment"},
    {name: "Done",                 color: GREEN,  description: "Closed"}
  ]}) { projectV2Field { ... on ProjectV2SingleSelectField { name } } }
}' >/dev/null
  PID=$(gh project view "$P" --owner "$OWNER" --format json --jq '.id')
  OPTMAP=$(gh project field-list "$P" --owner "$OWNER" --format json \
    --jq '.fields[] | select(.name=="Status") | .options[] | "\(.name)\t\(.id)"')
  while IFS=$'\t' read -r item old; do
    case "$old" in Ready) new="Ready for agent" ;; "In review") new="Needs human decision" ;; *) new="$old" ;; esac
    oid=$(awk -F'\t' -v n="$new" '$1 == n { print $2 }' <<<"$OPTMAP")
    gh project item-edit --id "$item" --project-id "$PID" --field-id "$FIELD" \
      --single-select-option-id "$oid" >/dev/null
  done <"$SNAP"
  log "Status options replaced and $(wc -l <"$SNAP") statuses restored"
fi

# --- 2. Gate field -----------------------------------------------------------
if gh project field-list "$P" --owner "$OWNER" --format json --jq '.fields[].name' | grep -qx Gate; then
  log "Gate field exists"
else
  gh project field-create "$P" --owner "$OWNER" --name Gate --data-type SINGLE_SELECT \
    --single-select-options "intent,spec,plan,PR review,merge/release" >/dev/null
  log "Created Gate field"
fi

# --- 3. Labels: kind of issue, never status ------------------------------------
gh label edit question --repo "$REPO" --description "A decision only a human can make"

# --- 4. Milestones: close the finished ones (all have 0 open issues), add releases ---
for n in 1 2 3 4 5 6 7 8 9; do
  gh api -X PATCH "repos/$REPO/milestones/$n" -f state=closed >/dev/null && log "  closed milestone $n"
done
for t in "$REL_A" "$REL_B" "$REL_C"; do
  if gh api "repos/$REPO/milestones?state=all" --jq '.[].title' | grep -qxF "$t"; then
    log "  milestone exists: $t"
  else
    gh api "repos/$REPO/milestones" -f title="$t" >/dev/null && log "  created milestone: $t"
  fi
done

# --- 5. Existing open issues ---------------------------------------------------
log "Placing existing open issues"
gh project item-add "$P" --owner "$OWNER" --url "$(url_of 396)" >/dev/null 2>&1 || true
set_field "$(url_of 396)" Status "Ready for agent"   # rate-limiter bug
for n in 421 249; do
  gh project item-add "$P" --owner "$OWNER" --url "$(url_of "$n")" >/dev/null 2>&1 || true
  set_field "$(url_of "$n")" Status Backlog
done
for n in 371 372; do # single-user for now (decision 2026-10-24); deferred, not closed
  if ! gh issue view "$n" --repo "$REPO" --json comments --jq '.comments[].body' | grep -qF "single-user for now"; then
    gh issue comment "$n" --repo "$REPO" --body "Deferred: prei is single-user for now (owner decision 2026-10-24). See plan.md \"Later\"." >/dev/null
  fi
done
# Non-goals in VISION.md. Uncomment after you decide:
# gh issue close 360 --repo "$REPO" --reason "not planned" --comment "MLS/RESO is a VISION.md non-goal."
# gh issue close 373 --repo "$REPO" --reason "not planned" --comment "1031 exchange is a VISION.md non-goal."

# --- 6. Work issues, one per plan.md row --------------------------------------
log "Creating plan.md row issues"
body() { # <plan row> <spec IDs> <exit criterion> <files>
  printf '## Plan row\n[plan.md](https://github.com/paruff/prei/blob/main/plan.md) %s\n\n## Spec\n%s in [spec.md](https://github.com/paruff/prei/blob/main/spec.md)\n\n## Exit criterion\n%s\n\n## Files\n%s\n\n## Design\nn/a: no UI\n' "$1" "$2" "$3" "$4"
}
A1=$(new_issue "Rentcast spike: key, TX/FL/TN coverage, latency" "$REL_A" Blocked "$(body A1 'FR-1, AC-1' 'Spike report committed: status, latency < 500ms, coverage for 5 ZIPs in TX/FL/TN.' 'scripts/ (one-off), docs/assessments/')")
gh issue comment "$A1" --body "Blocked: needs a Rentcast API key in .env (human sign-up)." >/dev/null 2>&1 || true
A2=$(new_issue "Rentcast adapter and rent fallback chain" "$REL_A" Backlog "$(body A2 'FR-1, AC-2, NFR-1' 'A HUD property screens with yield/PTR via the Rentcast fallback; tests cover each fallback step.' 'core/integrations/sources/rentcast_adapter.py, core/services/screening.py, core/integrations/health_monitor.py')")
A3=$(new_issue "ATTOM rent probe" "$REL_A" "Ready for agent" "$(body A3 'FR-2' 'Documented yes/no on the ATTOM rent field; if yes, adapter method plus tests.' 'core/integrations/sources/attom_adapter.py')")
A4=$(new_issue "GACS backtest script and report" "$REL_A" "Ready for agent" "$(body A4 'FR-3, AC-3, NFR-2' 'scripts/backtest_gacs.py runs; report with R², weights and sensitivity committed.' 'scripts/backtest_gacs.py, core/services/market_scoring.py')")
A5=$(new_issue "GACS signal completion: schools, supply, county employment" "$REL_A" Backlog "$(body A5 'FR-4' 'Each signal populated for test cities, with tests; employment prefers county QCEW.' 'core/integrations/market/schools.py, supply.py, core/services/market_scoring.py')")
B1=$(new_issue "FBI CDE retry with correct endpoint" "$REL_B" "Ready for agent" "$(body B1 'FR-5' 'Spike report: CDE returns agency-level data for a TX ZIP, or a documented failure.' 'core/integrations/market/crime.py')")
B2=$(new_issue "Crime adapter fallback source" "$REL_B" Backlog "$(body B2 'FR-5, AC-4, NFR-3' 'get_crime_score returns real ZIP-level data for test ZIPs.' 'core/integrations/market/crime.py')")
B3=$(new_issue "Async re-screen, discovery batch and VRM scrape" "$REL_B" Backlog "$(body B3 'FR-7, AC-6, NFR-4' 'Saving criteria returns in < 5s; re-screen completes in the background.' 'see plan.md B3')")
C1=$(new_issue "CSP, Permissions-Policy and CORP headers" "$REL_C" Backlog "$(body C1 'FR-9, AC-8' 'Headers present on all responses; middleware test.' 'settings.py, core/middleware/security_headers.py, requirements.txt')")
C2=$(new_issue "SRI on external scripts" "$REL_C" "Ready for agent" "$(body C2 'FR-9, AC-9' 'Every external script/link in base.html has integrity + crossorigin; unit test.' 'templates/base.html')")
C3=$(new_issue "Authenticated ZAP scan clean pass" "$REL_C" Backlog "$(body C3 'FR-9' 'CI zap-authenticated-scan: 0 FAIL, 0 WARN.' '.zap/, settings.py')")
DS=$(new_issue "Fix design-system drift: undefined tokens, chip colours, contrast, focus" "$REL_C" Backlog "$(body 'n/a: polish' 'n/a' 'All var(--x) defined in tokens.css; chips use palette tokens; primary button text ≥ 4.5:1; visible focus on inputs; no Bootstrap classes or template hex.' 'static/css/*.css, templates/markets/dashboard.html, templates/properties/financing_comparison.html, templates/portfolio.html')")

# --- 7. Manual steps -----------------------------------------------------------
cat >&2 <<EOF

Done. Board: https://github.com/users/$OWNER/projects/$P

Manual steps (built-in workflows are web-UI only): Project → ⋯ → Workflows
  1. "Auto-add to project": repository $REPO, filter  is:issue,pr is:open
  2. "Item added to project": Status = Backlog
  3. "Item closed" and "Pull request merged": Status = Done

Fill these into plan.md "Issue" column:
  A1 $A1   A2 $A2   A3 $A3   A4 $A4   A5 $A5
  B1 $B1   B2 $B2   B3 $B3
  C1 $C1   C2 $C2   C3 $C3
And in DESIGN.md replace "the \"Fix design-system drift\" issue (not yet created; ...)" with $DS
EOF

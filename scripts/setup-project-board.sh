#!/usr/bin/env bash
# One-shot setup of the "Real Estate Investor" board (project #3) for AGENTS.md "Workflow" and the
# goals in plan.md. Review, then run once from the repo root after the plan PR merges:
#   bash scripts/setup-project-board.sh
# Needs gh logged in with the `project` scope (check: gh auth status).
#
# Safe to re-run: skips Status options, fields, milestones, issues (matched by exact title),
# comments (matched by marker text) and closes that are already done.
set -euo pipefail

OWNER=paruff
REPO=paruff/prei
P=3
BOARD="Real Estate Investor"
G0="G0: runs in Docker, tested end to end"
G1="G1: find and decide (journey steps 1-4)"
G2="G2: buy and own (journey steps 5-7)"
G3="G3: grow (journey steps 8-9)"

log() { echo "$*" >&2; }
url_of() { echo "https://github.com/$REPO/issues/$1"; }
set_field() { # <issue url> <field> <value>
  gh project item-edit "$P" --owner "$OWNER" --url "$1" --field "$2" --value "$3" >/dev/null
  log "  $2=$3 <- $1"
}
set_status() { set_field "$1" Status "$2"; }
place() { # <issue number> <status>: add an existing issue to the board and set its Status
  gh project item-add "$P" --owner "$OWNER" --url "$(url_of "$1")" >/dev/null 2>&1 || true
  set_status "$(url_of "$1")" "$2"
}
existing_url() { # <exact title> -> URL of an issue with that title, or nothing
  gh issue list --repo "$REPO" --state all --limit 1000 --json title,url \
    --template '{{range .}}{{.title}}{{"\t"}}{{.url}}{{"\n"}}{{end}}' |
    awk -F'\t' -v t="$1" '$1 == t { print $2; exit }'
}
new_issue() { # <title> <milestone or ""> <status> <body> [blocked-by url] -> prints the issue URL
  local url
  url=$(existing_url "$1")
  if [ -n "$url" ]; then
    log "  exists: $url"
  else
    url=$(gh issue create --repo "$REPO" --title "$1" ${2:+--milestone "$2"} --project "$BOARD" \
      --body "$4" ${5:+--blocked-by "$5"})
    log "  created: $url"
  fi
  gh project item-add "$P" --owner "$OWNER" --url "$url" >/dev/null 2>&1 || true
  set_status "$url" "$3"
  echo "$url"
}
comment_once() { # <issue number> <marker text> <body>
  if gh issue view "$1" --repo "$REPO" --json comments --jq '.comments[].body' | grep -qF "$2"; then
    log "  comment already on #$1"
  else
    gh issue comment "$1" --repo "$REPO" --body "$3" >/dev/null
  fi
}
close_once() { # <issue number> <reason> <comment>
  if [ "$(gh issue view "$1" --repo "$REPO" --json state --jq .state)" = CLOSED ]; then
    log "  #$1 already closed"
  else
    gh issue close "$1" --repo "$REPO" --reason "$2" --comment "$3" >/dev/null
    log "  closed #$1 ($2)"
  fi
}
status_counts() { # <file of url<TAB>status> -> "status count" lines, sorted
  awk -F'\t' '{ c[$2]++ } END { for (s in c) print s "\t" c[s] }' "$1" | sort
}
body() { # <plan row> <spec IDs> <exit criterion> <files>
  printf '## Plan row\n%s in [plan.md](https://github.com/%s/blob/main/plan.md)\n\n## Spec\n%s in [spec.md](https://github.com/%s/blob/main/spec.md)\n\n## Exit criterion\n%s\n\n## Files\n%s\n\n## Design\nn/a: no UI\n' \
    "$1" "$REPO" "$2" "$REPO" "$3" "$4"
}

gh project view "$P" --owner "$OWNER" >/dev/null
gh project edit "$P" --owner "$OWNER" \
  --description "Status for $REPO. Goals and proof: plan.md. How it works: AGENTS.md Workflow." >/dev/null

# --- 1. Status options: rename Ready and In review in place, add Blocked -------
# Existing option IDs are passed back so every item keeps its value. A backup is taken first and
# checked afterwards; if any count changed, every item is restored from it.
BACKUP="${TMPDIR:-/tmp}/project-$P-status-$(date +%Y%m%d%H%M%S).tsv"
gh project item-list "$P" --owner "$OWNER" --limit 1000 --format json \
  --jq '.items[] | select(.content.url) | [.content.url, (.status // "")] | @tsv' >"$BACKUP"
log "Backed up $(wc -l <"$BACKUP" | tr -d ' ') item statuses to $BACKUP"

FIELD=$(gh project field-list "$P" --owner "$OWNER" --format json \
  --jq '.fields[] | select(.name=="Status") | .id')
opt() { # <option name> -> its id, or nothing
  gh project field-list "$P" --owner "$OWNER" --format json \
    --jq ".fields[] | select(.name==\"Status\") | .options[] | select(.name==\"$1\") | .id"
}
if [ -n "$(opt "Ready for agent")" ]; then
  log "Status options already set"
else
  # shellcheck disable=SC2016  # $f, $b... are GraphQL variables, not shell ones
  gh api graphql -f f="$FIELD" -f b="$(opt Backlog)" -f r="$(opt Ready)" -f i="$(opt "In progress")" \
    -f v="$(opt "In review")" -f d="$(opt Done)" -f query='
mutation($f: ID!, $b: String!, $r: String!, $i: String!, $v: String!, $d: String!) {
  updateProjectV2Field(input: {fieldId: $f, singleSelectOptions: [
    {id: $b, name: "Backlog",              color: GRAY,   description: "Not ready, or its goal has not started"},
    {id: $r, name: "Ready for agent",      color: BLUE,   description: "Only a human moves items here; agents pick from here"},
    {id: $i, name: "In progress",          color: YELLOW, description: "Claimed and being worked on"},
    {id: $v, name: "Needs human decision", color: PURPLE, description: "Waiting on a person; the Gate field names the decision"},
    {name: "Blocked",                      color: RED,    description: "Waiting on something named in the issue"},
    {id: $d, name: "Done",                 color: GREEN,  description: "Closed"}
  ]}) { projectV2Field { ... on ProjectV2SingleSelectField { options { name } } } }
}' --jq '"Status options: " + ([.data.updateProjectV2Field.projectV2Field.options[].name] | join(", "))' >&2

  AFTER="$BACKUP.after"
  gh project item-list "$P" --owner "$OWNER" --limit 1000 --format json \
    --jq '.items[] | select(.content.url) | [.content.url, (.status // "")] | @tsv' >"$AFTER"
  EXPECTED="$BACKUP.expected"
  awk -F'\t' -v OFS='\t' '$2=="Ready"{$2="Ready for agent"} $2=="In review"{$2="Needs human decision"} 1' \
    "$BACKUP" >"$EXPECTED"
  if [ "$(status_counts "$EXPECTED")" = "$(status_counts "$AFTER")" ]; then
    log "Item statuses unchanged by the rename"
  else
    log "Status counts changed. Restoring every item from $EXPECTED"
    while IFS=$'\t' read -r url status; do
      [ -n "$status" ] && set_status "$url" "$status"
    done <"$EXPECTED"
  fi
fi

# --- 2. Gate field: which human decision a Needs human decision item waits on --
if gh project field-list "$P" --owner "$OWNER" --format json --jq '.fields[].name' | grep -qx Gate; then
  log "Gate field already exists"
else
  gh project field-create "$P" --owner "$OWNER" --name Gate --data-type SINGLE_SELECT \
    --single-select-options "intent,spec,plan,PR review,merge/release" >/dev/null
  log "Created the Gate field"
fi

# --- 3. Labels: kind of issue, never status ------------------------------------
gh label edit question --repo "$REPO" --description "A decision only a human can make"

# --- 4. Milestones: close the old ones (all have 0 open issues), add one per goal ---
for n in 1 2 3 4 5 6 7 8 9; do
  if [ "$(gh api "repos/$REPO/milestones/$n" --jq .state)" = open ]; then
    gh api -X PATCH "repos/$REPO/milestones/$n" -f state=closed >/dev/null && log "  closed milestone $n"
  fi
done
for t in "$G0" "$G1" "$G2" "$G3"; do
  if gh api "repos/$REPO/milestones?state=all" --paginate --jq '.[].title' | grep -qxF "$t"; then
    log "  milestone exists: $t"
  else
    gh api "repos/$REPO/milestones" -f title="$t" \
      -f description="Outcome and proof: plan.md, section ${t%%:*}" >/dev/null && log "  created milestone: $t"
  fi
done

# --- 5. Goal issues, one per plan.md row ---------------------------------------
# Only the first rows of G0 start as Ready for agent; the rest wait in Backlog for their goal.
log "Creating goal issues"
G01=$(new_issue "G0.1 make docker-accept: acceptance suite against the container" "$G0" "Ready for agent" \
  "$(body G0.1 'FR-10, AC-11' 'make docker-accept builds, starts, seeds, runs tests/acceptance/ with BASE_URL at the container, and stops it. It may fail on app bugs; the target itself works.' 'Makefile')")
G02=$(new_issue "G0.2 docker compose up without the observability-lab network" "$G0" "Ready for agent" \
  "$(body G0.2 'FR-10, AC-10' 'On a machine with no observability-lab network, docker compose up gives a healthy /health/; OTEL export is optional.' 'docker-compose.yml')")
G03=$(new_issue "G0.3 One seed command for one market in the container" "$G0" Backlog \
  "$(body G0.3 'FR-11, AC-10' 'One make target seeds growth areas with GACS, properties and rent inputs for one market (default Dallas, TX) inside the container; make docker-dev uses the preiweb service.' 'Makefile, core/management/commands/')" "$G01")
G11=$(new_issue "G1.1 Journey scenario steps 1-4 against the container" "$G1" Backlog \
  "$(body G1.1 'FR-12, AC-12' 'A scenario identifies growth areas, discovers properties, screens with yield and price-to-rent, and underwrites one property, passing against the seeded container.' 'tests_bdd/features/journey.feature, tests_bdd/steps/')" "$G03")
G12=$(new_issue "G1.2 Rent report: coverage by source, HUD FMR vs Rentcast for its fee" "$G1" Backlog \
  "$(body G1.2 'NFR-7, NFR-1, AC-13' 'docs/assessments/rent-coverage.md committed: coverage by source on the seeded market, HUD FMR vs Rentcast quality and fee, and a recommendation on FR-1.' 'docs/assessments/rent-coverage.md, scripts/')" "$G03")
G21=$(new_issue "G2.1 Journey scenario steps 5-7 against the container" "$G2" Backlog \
  "$(body G2.1 'FR-13, AC-14' 'A scenario takes a screened property through offer, due diligence and closing to acquired, and finds it in the portfolio with monthly actuals, passing against the container.' 'tests_bdd/features/journey.feature, tests_bdd/steps/')" "$G11")
G22=$(new_issue "G2.2 Acquired property is complete at creation" "$G2" Backlog \
  "$(body G2.2 'FR-13' 'An acquired Property has purchase price, rent and expenses from the pipeline record (LIMIT-12 resolved).' 'core/services/ (pipeline acquisition)')" "$G21")
G31=$(new_issue "G3.1 Journey scenarios steps 8-9 against the container" "$G3" Backlog \
  "$(body G3.1 'FR-14, AC-15' 'Scenarios run BRRRR and leasing on a property acquired by G2.1 and pass against the container.' 'tests_bdd/features/journey.feature, tests_bdd/steps/')" "$G21")

# --- 6. In flight: #458 (CSP) waits on PR review --------------------------------
if [ "$(gh pr view 458 --repo "$REPO" --json state --jq .state)" = OPEN ]; then
  C1=$(new_issue "CSP, Permissions-Policy and CORP headers" "" "Needs human decision" \
    "$(body 'In flight (not a goal)' 'FR-9, AC-8' 'Headers present on all responses; implemented in #458.' 'investor_app/settings.py, core/middleware.py, templates/')")
  set_field "$C1" Gate "PR review"
  PR_BODY=$(gh pr view 458 --repo "$REPO" --json body --jq .body)
  if ! grep -qF "Closes $C1" <<<"$PR_BODY"; then
    gh pr edit 458 --repo "$REPO" --body "$PR_BODY

Closes $C1" >/dev/null
    log "  #458 now closes $C1"
  fi
fi

# --- 7. Existing open issues -----------------------------------------------------
log "Placing and closing existing issues"
place 396 "Ready for agent" # rate-limiter bug; no goal, so it sorts after goal items
for n in 369 421 249; do place "$n" Backlog; done
for n in 371 372; do
  comment_once "$n" "single-user for now" \
    "Deferred: prei is single-user for now (owner decision 2026-10-24). See plan.md \"Later\"."
done
close_once 360 "not planned" "Not planned: MLS/RESO integration is out of scope (spec.md \"Out of Scope\")."
close_once 373 "not planned" "Not planned: tax strategy and 1031 exchange tracking are out of scope (spec.md \"Out of Scope\")."
close_once 58 completed "Done: the passive-investing pivot is the product now (VISION.md). Remaining work is in plan.md goals G0-G3."

# --- 8. Manual steps and checks ---------------------------------------------------
cat >&2 <<EOF

Done. Board: https://github.com/users/$OWNER/projects/$P
Status backup: $BACKUP

Manual steps (built-in workflows can only be set in the web UI): Project → ⋯ → Workflows
  1. "Auto-add to project": repository $REPO, filter  is:issue,pr is:open
  2. "Item added to project": Status = Backlog
  3. "Item closed" and "Pull request merged": Status = Done
  4. "Pull request linked to issue": turn it off. It sets linked issues to "In progress",
     which would undo "Needs human decision".

Fill the issue URLs into the plan.md "Issue" column:
  G0.1 $G01   G0.2 $G02   G0.3 $G03
  G1.1 $G11   G1.2 $G12
  G2.1 $G21   G2.2 $G22
  G3.1 $G31

Checking both AGENTS.md Workflow commands:
EOF
gh project item-list "$P" --owner "$OWNER" --limit 200 --query 'status:"Ready for agent" is:open' --format json \
  --jq '.items | sort_by(.milestone.title // "~", .content.number) | .[0] | "next for an agent: #\(.content.number) \(.title) [\(.milestone.title // "no milestone key")]"' >&2
gh project item-list "$P" --owner "$OWNER" --limit 200 --query 'status:"Needs human decision" is:open' --format json \
  --jq '.items[] | "needs a human: \(.gate // "no gate key")\t#\(.content.number) \(.title)"' >&2

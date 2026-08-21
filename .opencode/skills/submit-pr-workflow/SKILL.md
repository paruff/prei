---
name: submit-pr-workflow
description: Use when finishing work and opening a pull request — run pre-commit, create a feature branch, commit with a conventional message, push, and open the PR. Also covers keeping the graphify knowledge graph in sync via the post-commit hook.
---

# Submit PR Workflow

## When to Use
- You have uncommitted changes ready to ship and the human has authorized a commit/PR.
- You are about to `git commit` on `main` (never commit directly to `main` — branch first).
- The repo enforces a commit-message regex in CI; you need to format the subject correctly.

## Guardrails (from AGENTS.md)
- Never push/merge to `main` directly. Always a feature branch + PR.
- One feature/fix per PR. If staged changes mix concerns, ask which to include.
- Exclude stray artifacts (e.g. `*.sqlite3-journal`, virtualenvs). Check `git status` before staging.

## Steps

### 1. Pre-commit
```bash
pre-commit run --files <changed files>   # scoped; faster than --all-files
```
Resolve every failure. `ruff-format` is check-only — apply fixes with
`ruff format <files>` then re-run. `mypy` errors must be fixed in code, not
skipped. Re-run until the overall check prints `ALL PASSED`.

### 2. Branch
```bash
git checkout -b <type>/<short-slug>        # feat/, fix/, refactor/, test/, docs/, chore/
```
Keep the branch focused on one change.

### 3. Stage intended files only
```bash
git add <specific files>                    # NOT `git add .` (avoids stray artifacts)
git status --short                          # confirm only intended files are staged
```

### 4. Commit (conventional, CI-enforced)
Subject MUST match (every commit in the PR is checked):
```
^(feat|fix|docs|style|refactor|test|chore|ci|perf|build|revert)(\(.+\))?: .{1,72}$
```
Validate before committing:
```bash
python3 -c "import re,sys;r=re.compile(r'^(feat|fix|docs|style|refactor|test|chore|ci|perf|build|revert)(\(.+\))?: .{1,72}\$');s=sys.argv[1];print(len(s),bool(r.match(s)))" "type(scope): subject"
```
First word after `type(scope):` must be lowercase. Put detail in the body.
```bash
git commit -m "type(scope): short subject

Body explains why, not what. Closes #issue"
```

### 5. Push + PR
```bash
git push -u origin <branch>
gh pr create --base main --title "type(scope): lowercase subject" --body "$(cat <<'EOF'
## What / Why / How / Testing / Checklist
EOF
)"
```
PR title first word (after `type(scope):`) must be lowercase.

### 6. Knowledge graph sync (graphify)
A `post-commit` hook (installed via `graphify hook install`) auto-rebuilds
`graphify-out/graph.json` on every commit — no action needed. To build the
graph for the first time or after doc changes, run the graphify skill on the
`core/` tree (code-only, free AST extraction). `graphify-out/` is gitignored.

## Common Mistakes
- Committing on `main` → branch first.
- `git add .` pulling in journals/artifacts → stage explicit paths.
- Subject > 72 chars → move detail to body.
- `fix(scope):` with capital first word → lowercase it.
- Skipping pre-commit because "CI will catch it" → fix locally first.

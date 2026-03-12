## Phase 1.7 — DORA CI Logging in GitHub Actions Workflow

### User Story
As an engineering lead, I want every CI job to emit structured DORA timestamps so that we can track deployment frequency, lead time, and pipeline health over time.

### Background
Per the Copilot instructions in `AGENTS.md`, all CI workflows must log:
```bash
echo "job-start: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "sha: ${{ github.sha }}"
echo "job-finish: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

The current `.github/workflows/ci.yml` does **not** include these log lines.

### Acceptance Criteria
- [ ] Add a `DORA: job start` step at the **beginning** of the `lint-and-test` job that prints:
  ```
  job-start: <ISO-8601 UTC timestamp>
  sha: <commit SHA>
  ```
- [ ] Add a `DORA: job finish` step at the **end** of the `lint-and-test` job that prints:
  ```
  job-finish: <ISO-8601 UTC timestamp>
  ```
- [ ] The `job-finish` step uses `if: always()` so it runs even when earlier steps fail
- [ ] Check `.github/workflows/docs.yml` and add the same DORA steps if that workflow has a job
- [ ] CI still passes (`ruff check` and `pytest -q` still succeed after the change)

### Files to Change
| File | Action |
|------|--------|
| `.github/workflows/ci.yml` | **Edit** — add DORA log steps |
| `.github/workflows/docs.yml` | **Edit** — add DORA log steps (if applicable) |

### Implementation Notes
- Use a `run:` step with a shell `echo` command; no external action needed
- `${{ github.sha }}` is a built-in GitHub Actions expression
- `$(date -u +%Y-%m-%dT%H:%M:%SZ)` gives UTC ISO-8601 in bash

### Example Step
```yaml
- name: "DORA: job start"
  run: |
    echo "job-start: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "sha: ${{ github.sha }}"
```

### Definition of Done
- CI workflow file contains both `job-start` and `job-finish` echo steps
- Workflow runs successfully on a PR and the log lines are visible in the Actions tab
- `if: always()` on the finish step is confirmed in the YAML

### Labels
`chore` `phase-1` `ci`

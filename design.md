# Design: Phase C (partial) — Deployment Reliability

### C-2: Authenticated ZAP scan runs against an ephemeral CI instance

Authenticating against the real deployed environment (what
`post-deployment.yml` targets) would require provisioning a scan account and
credentials on that live environment — the same category of infra gap as
C-1/C-3. Instead, a new `zap-authenticated-scan` job in `ci-quality.yml` runs
the authenticated scan against an ephemeral instance spun up inside the job
itself: fresh migrated SQLite DB, `runserver` bound to `0.0.0.0:8000`, scan
account seeded via a new idempotent management command
(`core/management/commands/seed_zap_scan_user.py`, mirroring the
`get_or_create`/`update_or_create` pattern in `seed_markets.py`).
`ZAP_AUTH_USERNAME` is a fixed, non-secret literal in the workflow;
`ZAP_AUTH_PASSWORD` is generated fresh each run (`secrets.token_urlsafe(24)`
in a "Generate throwaway scan credential" step, exported via `$GITHUB_ENV`) —
not a GitHub secret, since the DB is a throwaway SQLite file destroyed at job
end and the value never needs to be reused across runs.

`.zap/prei-auth-context.xml` defines form-based auth against
`/accounts/login/`, with logged-in/out indicator regexes (presence/absence of
`/accounts/logout/` and the password field) and a `<users>` entry containing
a `__ZAP_AUTH_CREDS_B64__` placeholder in place of a literal credential. A
"Render ZAP auth context" step substitutes the placeholder with a base64
`username=...&password=...` blob built from that run's generated password,
writing the result to `.zap/prei-auth-context-runtime.xml` (gitignored,
never committed) — rather than injecting via a `-P username=... -P
password=...` CLI flag as originally sketched, since `zap-full-scan.py`
doesn't expose a documented flag for that. This avoids ever committing a
credential-shaped value to git history; an earlier version of this file did
embed a static credential blob directly, which GitGuardian correctly flagged
as a hardcoded secret during PR review, prompting this runtime-templating
fix.

The job runs `zap-full-scan.py -a -n
/zap/wrk/.zap/prei-auth-context-runtime.xml -U zap-ci-scan-only` and is a
required check in `pr-gates-pass`, so it runs
pre-merge on every PR — a stronger "shift security left" posture than the
existing unauthenticated scan, which only runs post-deployment.
`post-deployment.yml`'s scan is left unchanged (defense in depth: one
authenticated pre-merge scan, one unauthenticated scan of the real artifact).

Scope decision recorded in `docs/KNOWN_LIMITATIONS.md` LIMIT-22.

### C-4: Flaky test detection, ledger, and quarantine

`pytest.ini`'s `addopts` gains `--report-log=.pytest-report.jsonl`, provided
by the `pytest-reportlog` plugin (not built into pytest core — this was a
wrong assumption in the original plan, corrected during implementation once
`--report-log` failed with "unrecognized arguments"). With
`pytest-rerunfailures` already wired (`--reruns 1 --reruns-delay 5`), a
rerun-then-pass test shows up in the report log as two `"call"`-phase
reports for the same nodeid: an intermediate `"rerun"` outcome followed by a
final `"passed"` outcome.

`.github/scripts/flaky_report.py` parses that JSONL file and detects exactly
that signature (`find_flaky_nodeids`). Two modes:

- `--mode report`: prints a markdown summary (also appended to
  `$GITHUB_STEP_SUMMARY` when set) without touching the ledger. Runs in
  `ci-quality.yml`'s `tests-unit`/`tests-integration`/`tests-e2e` jobs on
  every PR — visibility without any write contention between concurrent PR
  runs or fork-PR permission issues.
- `--mode write`: same summary, plus updates `docs/quality/flaky_tests.json`
  (nodeid → `count`, `first_seen`, `last_seen`, `quarantined`) and, once a
  nodeid's cumulative count reaches the threshold (default 3), adds it to
  `tests/.flaky_quarantine.txt`. Runs only from `docker-publish.yml`'s
  `live-test` job (push-to-`main` only) — the single writer for the shared
  ledger, avoiding merge conflicts between concurrent PRs.

Because `live-test`'s BDD suite runs inside a Docker container (`docker exec
... pytest tests_bdd/`), the report log is written to `/app/.pytest-report.jsonl`
inside the container (picked up automatically from `pytest.ini`'s `addopts`,
since the image includes it) and copied out via `docker cp` before the
container is torn down. If the ledger or quarantine file changed, the job
bot-commits as `github-actions[bot]` with `chore(ci): update flaky test
ledger [skip ci]` and pushes directly to `main` (the job's `permissions` gains
`contents: write` for this).

A new root `conftest.py` hook, `pytest_collection_modifyitems`, reads
`tests/.flaky_quarantine.txt` (if present) and marks matching nodeids
`pytest.mark.xfail(strict=False)` at collection time — quarantined tests keep
running and reporting on every run, but a known-flaky test can never fail the
build while it's being fixed. Verified end-to-end with a throwaway
deliberately-failing test converting to `1 xfailed`.

### Residual gap

The `docker-publish.yml` bot-commit step only runs on push-to-`main`, so it
can't be exercised from a PR branch. This is flagged in the PR description as
something to watch on the first post-merge run, not claimed as pre-merge
verified.

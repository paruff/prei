# Review — how to review code in prei

> Guidance for every reviewer, human or agent. Review the diff against its linked issue. What the product must do is in [`intent.md`](intent.md), [`spec.md`](spec.md) and [`plan.md`](plan.md). UI rules are in [`DESIGN.md`](DESIGN.md). Project rules and the review workflow are in [`AGENTS.md`](AGENTS.md).

## 1. What Important means here

| Severity | Meaning | Merge |
|---|---|---|
| **Important** | A concrete bug (an input or scenario that gives a wrong result, data loss or a crash), a security hole, or any item below | Blocks until fixed or answered |
| **Minor** | Clarity, naming, a simpler equivalent | Author decides |

Always Important in this repo:

- **Money:** currency as `float` anywhere, or finance math outside `investor_app/finance/utils.py` or `core/services/`.
- **Layers:** an external API call from a view (it must go through `core/integrations/` and a service), or a layer-direction violation ([docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)).
- **Co-changes:** a co-change listed in [docs/CHANGE_IMPACT_MAP.md](docs/CHANGE_IMPACT_MAP.md) that was left out.
- **Tests:** a behaviour change with no test that fails without it, or a test deleted, skipped or weakened to make CI pass.
- **Errors:** an exception swallowed in a check, validator or test without logging (AGENTS.md "Never Do" #10).
- **Approvals:** a migration, auth change, dependency change or workflow change without recorded human approval ([`migration-safety`](.agents/skills/migration-safety/SKILL.md)).
- **Size:** more than 400 changed lines without the `large-pr-approved` label.
- **Data sources:** a new data source not registered in `core/integrations/health_monitor.py`.

Write each finding as `file:line`, severity, the concrete failure, and a suggested fix.

## 2. Finding bugs

Read the changed code for these first. They are where this codebase breaks.

- **Money math:**
  - Decimal built from a float (`Decimal(0.1)`), or mixed Decimal and float arithmetic.
  - Rounding or `quantize` applied mid-calculation instead of at display.
  - Percentages stored as 8 vs 0.08.
- **Division by zero and missing inputs:**
  - Zero price, rent, ARV, debt service or units in CoC, Cap Rate, DSCR, GRM or the BRRRR calculations.
  - `None` from an adapter flowing into math.
- **Data-source results:**
  - An adapter returns nothing, a partial record or a stale cache, and the fallback chain skips or double-counts.
  - A score computed from a placeholder value without lowering its confidence (VISION principle 7).
  - Rate limits or budgets bypassed on retry.
- **Screening and scoring:**
  - A criterion silently skipped when its input is missing (for example `min_gacs_score` with no GACS).
  - Thresholds off by one (`>` vs `>=`).
  - Verdicts that disagree with the KPI colours.
- **Time:**
  - Naive vs aware datetimes.
  - Year boundaries in hold-period projections; month count vs month index.
- **Queries:**
  - N+1 queries in list views.
  - Unbounded querysets without pagination.
  - A queryset not filtered by `request.user`, which leaks another user's pipeline.
- **Views and forms:**
  - Double submit, and validation that only runs client-side.
  - Pipeline stage changes that skip a state.
- **Background or long work:**
  - A request that can exceed the 30s Gunicorn timeout.
  - A retry that repeats a paid API call.

## 3. Verification — does it work?

Run, or read the CI result for, each check. Quote the output; don't just say "tests pass".

| Check | Command |
|---|---|
| Lint and format | `make lint` (CI: `ruff check .`, `ruff format --check .`) |
| Django | `python manage.py check` and `python manage.py makemigrations --check --dry-run` |
| Tests | `make test` (CI also runs integration, e2e, acceptance and `tests/test_finance_math.py`) |
| Types | CI `typecheck` job (mypy on `core/` and `investor_app/finance/`) |
| Coverage | CI floor `--fail-under=70`. It must not drop. |
| UI change | Run the page at desktop width and at ≤ 640px. |

A red CI job is Important unless `flaky_report.py` lists it as a known flaky test.

## 4. Validation — is it the right thing?

- **Issue:** the change meets the linked issue's **Exit criterion**, no more.
- **Spec:** it satisfies the `spec.md` requirement and acceptance-criterion IDs the issue cites (e.g. FR-1, AC-2). If behaviour changed, `spec.md` changes in the same PR.
- **Plan:** it follows `plan.md` "Files that change" and "Order of work". Where it departs, `plan.md` is updated in the same PR.
- **Intent and scope:** nothing conflicts with `intent.md` or a [VISION.md](VISION.md) non-goal (single-user, SQLite for local, no MLS/RESO, no 1031, no canary or Kubernetes).
- **Design (UI):** cite the `DESIGN.md` section the change follows, or update `DESIGN.md` in the same PR. Use tokens, not raw values, and existing classes and partials.
- **Docs:** user-facing behaviour changes update `docs/`. `CHANGELOG.md` comes from release-please, never by hand.

## 5. Security

- No secrets, keys, tokens or PII in code, fixtures or logs. Settings come from env (see `.env.example`).
- Views: login required for user-owned data, querysets scoped to `request.user`, CSRF intact, and no `@csrf_exempt` without approval.
- Input: validated by forms or serializers at the boundary. No SQL built from strings. No `|safe`, `mark_safe` or `format_html` on user input.
- Outbound calls: timeouts set, paid-API budgets respected (`get_cost_tracking`), and failures logged and surfaced, never silent.
- Dependencies: justified (could stdlib or an installed package do it?), pinned in `requirements.txt`, and approved.
- Workflows: least-privilege `permissions:`, actions pinned by SHA, and untrusted input passed through `env:`, never interpolated.

## 6. Cap the nits

At most **3 Minor** findings per review, the most useful ones. If there are more, say "and N similar".

## 7. Do not report

- Anything `ruff`, `ruff format` or mypy already enforces.
- Style preferences with no effect on correctness or clarity.
- Pre-existing problems outside the diff. Open an issue if they matter.
- Speculative "might want to" refactors.

"No findings" is a valid review.

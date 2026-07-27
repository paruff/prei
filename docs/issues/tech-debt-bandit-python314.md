## Tech Debt — Reinstate Bandit once Python 3.14 support lands

> **Tracking issue:** open this file as a GitHub issue and pin/link it from `.bandit` and `.ruff.toml`.
> **Priority:** 🟢 Low (no active coverage gap — Ruff's `S` rule family is the active security-lint gate)

### Background

`docs/assessments/REPO_AUDIT_2026-07.md` (Finding 1, Phase 0) found that Bandit 1.8.0 crashes on
Python 3.14: it throws `AttributeError` on the removed `ast.Constant.s`/`.n` compat aliases,
catches the exception per-file, and silently reports "No issues identified" — meaning the gate had
been providing zero real coverage in CI and pre-commit.

**Resolution (Phase 0):** Bandit was removed from `.github/workflows/ci-quality.yml` and
`.pre-commit-config.yaml`. Ruff's `S` rule family (`.ruff.toml`) now mirrors Bandit's skip list
(`B101/B110/B112/B310/B311/B324` → `S101/S110/S112/S310/S311/S324`) and is the sole active
security-lint gate. `.bandit`'s config is preserved but unused, with a header comment explaining why.

### Exit condition

Upstream fix: [PyCQA/bandit#1219](https://github.com/PyCQA/bandit/issues/1219) (open as of 2026-07).
Once that ships in a released Bandit version:

1. Confirm the new release actually runs clean on Python 3.14 (`bandit -r core/ investor_app/`
   completes without the `ast.Constant` `AttributeError`).
2. Decide whether to reinstate Bandit alongside Ruff's `S` rules (defense-in-depth — Bandit and
   `flake8-bandit`/Ruff `S` don't have 100% identical rule coverage) or keep Ruff `S` as the sole
   gate now that it's proven itself in production.
3. If reinstating: restore the `bandit` step in `ci-quality.yml`'s `lint` job and the pre-commit
   hook, remove the "NOT CURRENTLY USED" header from `.bandit`.

No action needed until the upstream issue closes.

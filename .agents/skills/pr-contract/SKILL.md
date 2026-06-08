> Load with: "pr-contract skill" in your prompt
> Example: "Use the pr-contract skill to implement this feature."

# PR Contract Skill — prei

## PM–Agent contract
- PM writes scoped issue with acceptance criteria and file targets.
- Agent implements minimal diff, updates tests/docs, and opens draft PR.
- Human reviewer approves/rejects, requests revisions, and owns merge decision.
- Agent must surface risks, assumptions, and unresolved questions in PR description.

## PR size limit and enforcement
- Target PR size: < 400 changed lines.
- If over limit, split into sequenced PRs or request explicit human `large-pr-approved` decision.
- CI/review policy blocks merge when required approval is missing.

## Required PR description block (AI-Assisted Review Block)
Include all:
1. One-sentence change summary.
2. Top 2–3 likely failure modes.
3. Tests that cover the change.
4. Architecture check confirmation.
5. Judgment calls requiring human review.

## Agents MAY do without asking
- Edit application code, tests, and docs inside scoped files.
- Run lint/format/tests and `python manage.py check`.
- Open draft PRs and request review.

## Agents MUST ask before doing
- Adding/updating dependencies.
- Creating/modifying migrations.
- Changing `.github/workflows/`.
- Altering authentication/authorization/security policy behavior.
- Expanding scope beyond agreed files or >5 files.

## Agents must NEVER do
- Commit secrets, credentials, or production data.
- Merge PRs or push directly to `main`.
- Delete tests to make CI pass.
- Bypass required human approvals.

## Coding standards
- Naming: snake_case functions/variables, clear domain names.
- Types: type hints required on new public functions.
- Tests: failing test first, then implementation, then regression checks.
- Commits: conventional prefixes (`feat:`, `fix:`, `docs:`, `test:`, `chore:`, `refactor:`).
- Coverage: add or update tests for new/changed behavior; include edge cases for finance logic.

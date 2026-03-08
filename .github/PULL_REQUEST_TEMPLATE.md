## What This PR Does

<!-- One sentence. -->

## Closes

<!-- Issue number(s): Closes #N -->

-----

## AI-Assisted Review Block

<!-- REQUIRED. Complete before requesting review. Use Copilot or @review-agent to help fill this in. -->

<!-- DORA 2025 (REVIEW-01): Structured review blocks reduce review time by making context explicit. -->

**What does this PR do in one sentence?**

<!-- Ask Copilot: "Summarise this diff in one sentence for a PR description" -->

**What are the top 2–3 failure modes?**

<!-- Ask Copilot: "What are the most likely ways this diff could fail in production?" -->

**What tests cover this change?**

<!-- List test files. If none: explain why, or add tests before requesting review. -->

**Architecture check:**

<!-- Ask Copilot: "Does this diff violate any rules in .github/copilot-instructions.md?" -->

- [ ] No financial math directly in views or models (all in `investor_app/finance/utils.py` or `core/services/`)
- [ ] No external API calls in views (all in `core/integrations/`)
- [ ] No `float` used for currency — Decimal throughout
- [ ] No `any` type in new code

**What I was NOT sure about (flag for human review):**

<!-- Any judgment call, ambiguous requirement, or edge case you deferred to the reviewer. -->

-----

## Checklist

- [ ] `ruff check . && black --check . && pytest -q` passes (lint + format + tests)
- [ ] PR is < 400 changed lines, OR `large-pr-approved` label has been applied by a human
- [ ] No secrets or credentials in any changed file
- [ ] New features are behind a feature flag (if applicable)
- [ ] `docs/` updated if any public service or utility function changed

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

- [ ] No Firebase SDK calls in `screens/` or `components/`
- [ ] No business logic in screen files
- [ ] No inline type definitions (all types in `src/types/index.ts`)
- [ ] No `any` in catch blocks

**What I was NOT sure about (flag for human review):**

<!-- Any judgment call, ambiguous requirement, or edge case you deferred to the reviewer. -->

-----

## Checklist

- [ ] `npm run preflight` passes (lint + typecheck + tests)
- [ ] PR is < 400 changed lines, OR `large-pr-approved` label has been applied by a human
- [ ] No secrets or credentials in any changed file
- [ ] New features are behind a feature flag (if applicable)
- [ ] `docs/` updated if any public service or utility function changed

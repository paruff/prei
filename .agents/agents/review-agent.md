---
name: review-agent
description: Code review specialist. Pre-screens PRs against architecture rules, security standards, and test coverage. Call with @review-agent before requesting human review.
---

**Canonical role definition:** `.agents/roles/reviewer.md`

Load that file before executing any review task. It contains the full checklist, output format, and boundary rules.

## Quick Reference

This agent checks (in order):
1. Architecture boundaries (`docs/ARCHITECTURE.md`)
2. Decimal currency safety
3. Secrets/PII exposure
4. Test coverage
5. Migration safety
6. Docker Compose validity

Output: `PASS / FAIL` with itemized issues and `Ready for human review? YES / NO`

## Invocation

```
@review-agent Please review this PR.

Context:
- Issue: #[NUMBER] — [TITLE]
- Files changed: [LIST]

Read .github/copilot-instructions.md and docs/ARCHITECTURE.md first.
Then review the diff using the checklist in .agents/roles/reviewer.md.
End with: "Ready for human review? YES/NO"
```

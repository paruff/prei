# Copilot Budget Admin Checklist

## 3-step org setup
1. Configure monthly budget caps and alert thresholds in Copilot billing settings.
2. Enable credit pooling and set team-level soft limits.
3. Enforce Code Review policy: human review required for all AI-assisted PRs.

## Weekly admin ritual
- `gh run list --limit 100 --json workflowName,conclusion,createdAt`
- `gh pr list --state open --limit 100 --json number,author,createdAt,additions,deletions`
- Review billing dashboard model/mode breakdown and compare to weekly budget burn.
- Flag top outliers and schedule coaching (scope, mode, model routing).

## Heavy-user conversation (constructive)
- Start with shared goal: preserve velocity while staying inside budget.
- Review actual usage patterns (mode, model, context size) instead of blame.
- Agree on 2 concrete changes (scope-first prompts, cheaper default model, Ask mode for analysis).
- Re-check after one week and celebrate improvement.

## Budget targets by team size (monthly planning baseline)
| Team size | Suggested monthly budget target |
|---|---:|
| 1-3 devs | 5,000 credits |
| 4-8 devs | 15,000 credits |
| 9-15 devs | 30,000 credits |
| 16+ devs | 60,000+ credits (tiered by squad) |

## Promotional credit reminder
If a promotional credit period is active, log end date now and set renewal reminders 30 and 7 days before expiration.

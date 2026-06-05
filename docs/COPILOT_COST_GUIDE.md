# Copilot Cost Guide — prei

## Billing model (plain language)
Since June 2026, Copilot usage is metered in AI Credits (1 credit = $0.01). Input and output tokens consume credits based on model class. Free/base chat features may exist by plan, but premium model usage, coding-agent tasks, and long-context requests drive billable credit spend.

## Plan credit budgets (example planning baseline)
| Plan | Typical monthly credits | Team budgeting note |
|---|---:|---|
| Pro | 300 | Individual cap; watch premium model spikes |
| Pro+ | 1,500 | Good for heavier solo workflows |
| Business | Org-managed pooled budget | Set caps per user/team |
| Enterprise | Org-managed pooled + policy controls | Use governance and model routing policies |

> Confirm exact entitlements in your GitHub billing dashboard, as plan terms can change.

## Top three cost levers (highest impact first)
1. **Instruction file size (always-on context):** Every line in AGENTS/copilot instructions is paid repeatedly.
2. **Mode selection (Ask vs Agent):** Agent mode drives larger context and more tool calls.
3. **Model selection (cheap vs frontier):** Frontier models amplify per-token spend.

## Anti-patterns and lower-cost alternatives
| Anti-pattern | Cost impact | Better pattern |
|---|---|---|
| Monolithic AGENTS.md with all policies | High recurring input burn | Keep always-on <=80 lines; move details to skills |
| Using Agent mode for quick Q&A | Overpays for orchestration | Use Ask mode for analysis-only tasks |
| Defaulting to frontier model | 3x-30x multipliers | Route by task complexity |
| Unscoped prompts across many files | Inflated context payload | Scope-first protocol with explicit file lists |

## Before/after style cost examples
- **Before:** 4,500 always-on tokens, 20 tasks/day, Sonnet-class input pricing -> about $11.88/month input cost.
- **After:** 320 always-on tokens, same usage -> about $0.84/month input cost.
- **Effect:** ~93% reduction in recurring always-on input spend.

## Typical monthly scenarios for prei
Assume always-on context near 320 tokens and Sonnet-class input pricing (~$0.003/1k):

| Usage pattern | Tasks/day | Estimated monthly input cost |
|---|---:|---:|
| Light maintenance | 10 | ~$0.21 |
| Normal feature flow | 20 | ~$0.42 |
| Heavy sprint | 50 | ~$1.06 |

> Actual spend also includes output tokens and model multiplier effects.

## Reading the GitHub billing dashboard
1. Open GitHub org/user billing and Copilot usage view.
2. Filter by date range (current month, prior month).
3. Break down by model and feature (chat, agent, reviews).
4. Compare burn rate vs monthly budget and forecast remaining days.
5. Investigate outliers (heavy users, frontier model spikes, long-context prompts).

## Team admin controls
- Set monthly budget caps and alerts.
- Use pooled credits with per-team guardrails.
- Restrict frontier models unless approved.
- Enforce review policy for expensive workflows (agent and code review usage).

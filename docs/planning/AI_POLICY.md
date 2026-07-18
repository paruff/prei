# AI Policy — [PROJECT NAME]

> DORA AI Cap 1 finding: “A clear AI stance provides psychological safety for
> experimentation. Ambiguity around AI use creates friction, reduces adoption,
> and harms team morale.”
>
> DORA 2025 finding: “30% of developers report little or no trust in AI-generated
> code — and having appropriate skepticism is correct. The policy response is
> clarity, not mandated trust.”
>
> This document is the official AI policy for this project. Reviewed quarterly.

-----

## Our AI Stance

We use AI agents to accelerate software delivery. We do not use AI to replace
human judgment, architectural decisions, or quality accountability.

**AI implements. Humans decide.**

-----

## What AI Is Used For

|Use Case                     |Tool                |Human Oversight                      |
|-----------------------------|--------------------|-------------------------------------|
|Code generation from PM specs|GitHub Copilot agent|Human review before merge            |
|Test generation              |`@test-agent`       |Human confirms tests are meaningful  |
|Documentation generation     |`@docs-agent`       |Human reviews for accuracy           |
|Code review pre-screening    |`@review-agent`     |Human makes final review decision    |
|Security scanning            |`@security-agent`   |Human escalates all CRITICAL findings|
|Debugging assistance         |Copilot Chat        |Human verifies the fix               |

-----

## What AI Is NOT Used For

- Architectural decisions (which patterns, where code lives, how layers are structured)
- Security-sensitive configuration (auth flows, secret management, Firestore rules)
- Adding new dependencies (requires PM + human developer sign-off)
- Merging PRs (humans merge — always)
- Responding to production incidents (humans lead; AI assists with investigation)

-----

## Psychological Safety Norms (DORA 2025 PSYCH-01)

> DORA 2025: “Psychological safety is strongly predictive of high software delivery
> performance — and AI adoption without psychological safety creates anxiety, not productivity.”

**Team agreements:**

1. **Anyone may decline AI assistance on any task.** No justification required.
1. **AI skepticism is not resistance to change.** Questioning AI output is encouraged — it is the review process working correctly.
1. **Mistakes with AI-generated code are learning opportunities**, not failures. The review process is designed to catch them.
1. **Concerns about AI quality or direction** are raised openly — in retrospectives, in the DEVEX_LOG, or directly to the PM.
1. **Human judgment overrides AI output** in all cases, without friction.

-----

## Data Handling

[PLACEHOLDER — fill in your actual data policy. Example:]

- **Acceptable context for AI:** Source code, internal architecture docs, non-PII test data
- **Not acceptable:** Customer PII, credentials, production database contents, private keys
- **Where prompts are processed:** [GitHub Copilot / your AI provider] — see their data retention policy
- **Logging:** AI sessions are not logged beyond what the AI provider retains

-----

## Accountability

- **Who sets AI policy:** [PM / Tech Lead / both] — reviewed quarterly
- **Who owns the instructions files:** Human developers — agents cannot modify `AGENTS.md`
- **How we handle AI-introduced bugs:** Follow `docs/RUNBOOKS.md` → Change Failure Response
- **Who approves large PRs:** Human reviewer only — the `large-pr-approved` label is humans-only

-----

## Policy Review Cadence

This document is reviewed quarterly. Trigger a review if:

- Rework rate exceeds 20% for two consecutive months
- A new AI capability is being adopted (new agent, new tool)
- A significant AI-introduced incident occurs in production
- Team DevEx score for “AI Trust” falls below 3

**Last reviewed:** [PLACEHOLDER — date]
**Next review:** [PLACEHOLDER — date]

# Metrics — [PROJECT NAME]

> DORA 2025 (METRICS-02): Rework rate added as a new core metric alongside the
> traditional four. “AI-assisted teams that don’t track rework see throughput gains
> consumed by hidden instability.”
>
> Run `python manage.py check && pytest -q` for the weekly snapshot. Update this doc monthly.

-----

## The Five Metrics We Track

|Metric                        |Target  |⚠️ Warning|❌ Stop  |Tool                       |
|------------------------------|--------|---------|--------|---------------------------|
|**Rework rate**               |< 10%   |10–20%   |> 20%   |GitHub Insights            |
|**Change failure rate**       |< 5%    |5–15%    |> 15%   |Error monitoring           |
|**PR revision rate**          |< 25%   |25–40%   |> 40%   |GitHub Insights            |
|**Lead time (issue → deploy)**|< 3 days|3–7 days |> 7 days|GitHub Projects            |
|**CI cycle time**             |< 4 min |4–8 min  |> 8 min |GitHub Actions             |

-----

## Rework Rate (New in DORA 2025)

**Definition:** Lines substantially changed or reverted within 14 days of being authored,
as a percentage of total lines authored in the period.

**Why it matters:** Rework rate is the earliest signal that AI output quality is degrading
or that `AGENTS.md` / `copilot-instructions.md` needs updating.

**Response protocol:**

- **0–10%:** Healthy. Copilot output is landing well.
- **10–20%:** Watch. Check for prompt pattern drift. Run a PROCESS tuning session.
- **> 20%:** Stop adding features. Fix the instructions first. Review `docs/PROMPT_LIBRARY.md` changelog.

**Measurement:**

```bash
python manage.py check && pytest -q  # check project health and run all tests
```

-----

## Change Failure Rate

**Definition:** Percentage of deploys that cause a user-visible bug, crash, or required rollback.

**Response protocol:**

1. Deploy causes error spike → automated alert fires
1. Follow `docs/RUNBOOKS.md` → Change Failure Response runbook
1. Root cause: Was it a Copilot pattern failure? Update `AGENTS.md`.
1. Root cause: Was it an untested edge case? Add regression test.

-----

## PR Revision Rate

**Definition:** Percentage of PRs requiring at least one revision request before merge.

A rising PR revision rate means one of:

- Issues are too vague (PMs need to write better specs)
- Copilot is not following architecture rules (update `AGENTS.md`)
- Review is inconsistent (update `docs/RUNBOOKS.md` review checklist)

-----

## Developer Experience (DevEx) Score

> DORA 2025: “The platform capability most correlated with positive developer experience
> is giving clear feedback on the outcome of tasks.”

Track monthly in `docs/DEVEX_LOG.md`. Five dimensions, scored 1–5:

|Dimension       |Question                                                 |Target|
|----------------|---------------------------------------------------------|------|
|Flow            |How often do I reach flow state?                         |≥ 4   |
|Feedback Speed  |How fast does the system tell me when something is wrong?|≥ 4   |
|Cognitive Load  |How much mental effort does the codebase require?        |≤ 3   |
|AI Trust        |How often do I accept Copilot output with confidence?    |≥ 3   |
|Tooling Friction|How often does a tool block my work?                     |≤ 2   |

**Trigger:** Any dimension < 3 for two consecutive months → file an improvement issue.

-----

## Monthly Metrics Log

|Month        |Rework Rate|Change Failure|PR Revision|Lead Time|CI Time|DevEx Avg|
|-------------|-----------|--------------|-----------|---------|-------|---------|
|[PLACEHOLDER]|—          |—             |—          |—        |—      |—        |

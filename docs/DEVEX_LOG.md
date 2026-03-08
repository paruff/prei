# Developer Experience Log — [PROJECT NAME]

> DORA 2025 (DEVEX-01): “The platform capability most correlated with positive developer
> experience is giving clear feedback on the outcome of tasks.”
> Monthly self-assessment. 5 minutes. Last Friday of each month.
> See `docs/RUNBOOKS.md` → Monthly DevEx Review for instructions.

-----

## Scoring Guide

**1** — Strongly disagree / very poor
**2** — Disagree / poor
**3** — Neutral / acceptable
**4** — Agree / good
**5** — Strongly agree / excellent

-----

## Monthly Log

|Month        |Flow|Feedback Speed|Cognitive Load*|AI Trust|Tooling Friction*|Notes      |
|-------------|----|--------------|---------------|--------|-----------------|-----------|
|[PLACEHOLDER]|    |              |               |        |                 |First entry|

*Lower is better for Cognitive Load and Tooling Friction. Target ≤ 3.

-----

## Trigger Table

|Condition                                     |Action                                                               |
|----------------------------------------------|---------------------------------------------------------------------|
|Any dimension < 3 for 1 month                 |Note and monitor                                                     |
|Any dimension < 3 for **2 consecutive months**|**File an improvement issue immediately**                            |
|Cognitive Load ≥ 4 for 1 month                |Run Value Stream Mapping — codebase may have accumulated complexity  |
|AI Trust < 3 for 1 month                      |Review `AGENTS.md` and `docs/PROMPT_LIBRARY.md` — update instructions|
|Tooling Friction ≥ 4 for 1 month              |File a developer platform improvement issue                          |
|Flow < 3 for 2 months                         |Review sprint batch size — tasks may be too large or poorly scoped   |

-----

## Dimension Definitions

**Flow** — How often do development sessions produce a state of sustained focus and momentum?

- Score 5: Almost every session
- Score 1: Constant interruptions; rarely finish a task without switching context

**Feedback Speed** — How quickly does the system (CI, tests, Copilot, linter) tell me when something is wrong?

- Score 5: Errors surface within seconds–minutes
- Score 1: I only learn something is wrong when it reaches production

**Cognitive Load** — How much mental effort does navigating the codebase and tooling require?

- Score 1 (target): The codebase is clear; architecture is predictable; tooling is transparent
- Score 5 (problem): I have to hold too many things in my head; the code is hard to navigate

**AI Trust** — How often do I accept Copilot output with confidence vs. needing to substantially rewrite?

- Score 5: Output is almost always correct and architecturally sound
- Score 1: I spend more time correcting AI output than I save

**Tooling Friction** — How often does a tool, script, CI step, or process block or slow my work?

- Score 1 (target): Tools work; CI is fast; scripts are reliable
- Score 5 (problem): Frequent tool failures, slow CI, scripts that need babysitting

-----

## Improvement Issues Filed

|Month        |Dimension Triggered|Issue Filed|Outcome|
|-------------|-------------------|-----------|-------|
|[PLACEHOLDER]|                   |           |       |

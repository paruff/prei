# Team Archetype Self-Assessment — [PROJECT NAME]

> DORA 2025: “Seven team archetypes experience AI adoption differently and require
> different interventions. Without accurate self-assessment, teams misallocate AI investment.”
>
> Complete this before Phase 1 work begins. Revisit quarterly.
> The archetype determines which controls to add first.

-----

## The Seven Archetypes

|#|Archetype                    |Key Signals                                  |AI Risk                                     |
|-|-----------------------------|---------------------------------------------|--------------------------------------------|
|1|**Foundational Challenges**  |Survival mode, process gaps, high burnout    |AI accelerates chaos                        |
|2|**Legacy Bottleneck**        |Unstable systems, constant firefighting      |AI speeds code; broken deploy consumes gains|
|3|**Constrained by Process**   |Slow, bureaucratic workflows                 |AI creates friction with process overhead   |
|4|**High Impact, Low Cadence** |Quality work, slow delivery, low stability   |Need automation to unlock cadence           |
|5|**Stable and Methodical**    |Deliberate, high quality, consistent delivery|AI can safely accelerate here               |
|6|**Pragmatic Performers**     |Fast, functional, effective delivery         |AI creates PR review backlog at scale       |
|7|**Harmonious High-Achievers**|Virtuous cycle: well-being + performance     |AI multiplies advantages                    |

-----

## Self-Assessment

**Date:** [PLACEHOLDER]

### Evidence from the last 30 days

|Indicator                           |Measurement      |
|------------------------------------|-----------------|
|Deployment frequency                |deploys / week   |
|Average PR cycle time (open → merge)|days             |
|Change failure rate                 |%                |
|Rework rate                         |%                |
|DevEx score                         |/5 (if available)|
|Team friction observations          |[describe]       |

### Archetype selection

**Our closest archetype:** [PLACEHOLDER — e.g. “5 — Stable and Methodical”]

**Reasoning:** [PLACEHOLDER — 2–3 sentences explaining why this fits]

**The two or three weakest DORA AI capabilities for our archetype:**

1. [PLACEHOLDER]
1. [PLACEHOLDER]

-----

## Archetype-Specific Priority Adjustments

### If Archetypes 1 or 2 (Foundational / Legacy Bottleneck)

**Elevate first:** CI/CD stability, observability, error monitoring, Django/DRF auth & permissions, Postgres migrations, secrets management
**Logic:** Fix stability before accelerating throughput. AI on an unstable foundation accelerates instability.
**Defer:** Prompt library, advanced agents, feature velocity

### If Archetype 3 (Constrained by Process)

**Elevate first:** Small batch enforcement, PR process streamlining, bottleneck removal
**Logic:** Reduce friction first. AI will amplify remaining friction.
**Defer:** New feature work until flow is improved

### If Archetype 4 (High Impact, Low Cadence)

**Elevate first:** Deploy automation, CI speed, environment promotion
**Logic:** Automation to unlock deployment frequency before adding AI velocity
**Defer:** Advanced prompt engineering until deploy pipeline is reliable

### If Archetypes 5 or 6 (Stable / Pragmatic Performers)

**Proceed as planned.** Current implementation order is appropriate.
**Watch for:** PR review becoming a bottleneck as AI increases PR volume. Elevate REVIEW-01.

### If Archetype 7 (Harmonious High-Achievers)

**Accelerate:** Feature velocity. Foundation is sound.
**Focus on:** Metrics visibility to maintain advantage as scale increases

-----

## Priority Adjustments Made (Based on This Assessment)

[PLACEHOLDER — list any issues elevated or deferred from the master implementation index]

|Issue ID|Original Phase|New Priority|Reason|
|--------|--------------|------------|------|
|        |              |            |      |

-----

## Quarterly Re-assessment

Review cadence: first week of each quarter.

Questions to ask:

- Has deployment frequency or stability changed significantly?
- Has team composition changed?
- Has the rework rate or DevEx score shifted by more than 1 point?
- If yes to any: re-run this assessment and update the priority adjustments

**Next review date:** [PLACEHOLDER]

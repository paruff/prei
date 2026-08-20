# Model Routing Guide — prei

## Mode decision tree
```
Start
  |
  +-- Need code changes?
  |      |
  |      +-- No -> Ask mode
  |      |
  |      +-- Yes
  |            |
  |            +-- <=2 files and low risk? -> Edit mode
  |            |
  |            +-- Multi-step / tests / docs / uncertain scope? -> Agent mode
  |
  +-- High-risk area (auth/migration/workflows/deps)?
         |
         +-- Yes -> ask for human approval first
```

## Model selection table
| Model tier | Cost multiplier (relative) | Best for | Example tasks |
|---|---:|---|---|
| Cheap (GPT-4.1/mini class) | 1x baseline | Routine coding/docs/tests | serializer update, docs fix, simple service patch |
| Mid (Sonnet/Codex class) | ~2x-5x | Complex refactors/query optimization | multi-join queryset tuning, cross-module service cleanup |
| Frontier (Opus-class) | ~10x-30x | Rare deep design trade-off analysis | architecture alternatives with explicit approval |

## Scope-before-you-start protocol (paste to agent)
```
Scope check:
- Read first: <up to 5 files>
- Write: <expected file list>
Plan: I will implement the smallest change that satisfies acceptance criteria and preserve existing behavior. I will run project checks and report blockers before handoff.
```

## Four expensive anti-patterns
1. Frontier model by default for routine tasks.
2. Agent mode used for simple read-only questions.
3. Massive always-on instructions loaded every request.
4. Repeated rework due to vague prompt scope and no file targets.

## Cost comparison examples
| Pattern | Approx relative cost |
|---|---:|
| Ask + cheap model + scoped prompt | 1x |
| Agent + cheap model + scoped prompt | 2x-4x |
| Agent + mid model + broad prompt | 5x-12x |
| Agent + frontier model + broad prompt | 15x-40x |

## Local model strategy (Ollama available)
- Use local models for drafting PR text, summarization, and brainstorming.
- Keep hosted models for repository-aware edits and CI-sensitive tasks.
- Never include secrets or production data in local model prompts.

## One-sentence routing rule
Use the cheapest mode and model that can reliably complete the task, and escalate only after a scoped attempt fails.

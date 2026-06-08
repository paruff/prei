> Load with: "model-routing skill" in your prompt
> Example: "Use the model-routing skill to implement this feature."

# Model Routing Skill — prei

## Mode decision table
| Mode | Use when | Avoid when |
|---|---|---|
| Ask | Q&A, clarifications, code reading, risk analysis | Multi-file edits or execution-heavy tasks |
| Edit | Small scoped changes in <=2 files | Cross-cutting refactors or uncertain scope |
| Agent Mode | Multi-step implementation with tests/docs updates | Unclear requirements or high-risk changes without approval |

## Model decision table
| Tier | Model class | Typical use | Cost stance |
|---|---|---|---|
| Cheap | GPT-4.1 / mini-class | Docs, simple edits, straightforward Django changes | Default |
| Mid | Sonnet-class / codex mid-tier | Complex service refactors, tricky query composition | Use only with clear scope |
| Frontier | Opus/frontier-class | Deep architecture tradeoff analysis with human-in-loop | Exception-only |

## Scope check protocol (run before Agent Mode)
1. List files to read first (max 5).
2. List files expected to change.
3. Write a 2-sentence execution plan before editing.
4. If scope expands, pause and request confirmation.

Paste-ready text:
```
Scope check:
- Read: <files>
- Write: <files>
Plan: I will make the smallest change that satisfies acceptance criteria and preserve current behavior. I will run project checks and report any blockers before handoff.
```

## Local model guidance (if Ollama is available)
- Use local models for prompt drafting, summarization, and non-sensitive brainstorming.
- Use hosted models for repository-aware edits, CI-aware reasoning, and final code diffs.
- Never move secrets/PII into local prompts.

## Reference
- `docs/MODEL_ROUTING_GUIDE.md`

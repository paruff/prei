> Load with: "evaluation skill" in your prompt
> Example: "Use the evaluation skill to score agents on this feature."

# Evaluation Skill — prei

## When to use

After human review of a feature or bugfix, score each agent's contribution. This creates a feedback loop that improves agent accuracy over time.

## Scoring protocol

After each feature/bugfix is merged, append a JSONL entry to `.agents/memory/agent_scores.jsonl`.

### Entry format

```json
{
  "ts": "2026-06-08T14:30:00Z",
  "feature": "saved-search",
  "pr": "#42",
  "agents": {
    "planner": {
      "completeness": 4,
      "risk_accuracy": 5,
      "scope_estimation": 3,
      "notes": "Missed the migration task, but risk flags were accurate"
    },
    "coder": {
      "first_pass_success": 4,
      "test_quality": 5,
      "diff_minimalism": 5,
      "notes": "Clean implementation, good edge case tests"
    },
    "reviewer": {
      "false_positives": 0,
      "false_negatives": 1,
      "actionable_feedback": 4,
      "notes": "Missed the Decimal precision issue in cap_rate"
    },
    "test_writer": {
      "edge_case_coverage": 4,
      "test_soundness": 5,
      "notes": "Good BDD scenarios, solid fixture usage"
    }
  },
  "human_corrections": [
    "Added migration task that planner missed",
    "Fixed Decimal precision in cap_rate that reviewer missed"
  ]
}
```

**Only include agents that were actually used.** If security step was skipped, omit the `security` key entirely. If the feature didn't need the planner, omit `planner`.

### Scoring scale

| Score | Meaning |
|-------|---------|
| 5 | Excellent — no human correction needed |
| 4 | Good — minor adjustments, agent was mostly right |
| 3 | Adequate — agent got the gist but missed important details |
| 2 | Poor — significant human rework required |
| 1 | Failed — agent output was wrong or misleading |

### What to score per agent

**planner**
- `completeness`: Did the task graph cover everything? (1 = missed critical tasks, 5 = complete)
- `risk_accuracy`: Were risk flags correct? (1 = wrong risks flagged, 5 = all risks caught)
- `scope_estimation`: Was the file/task count accurate? (1 = wildly off, 5 = within 1)

**coder**
- `first_pass_success`: Did implementation pass review on first try? (1 = failed review, 5 = clean pass)
- `test_quality`: Are tests meaningful? (1 = just "it runs", 5 = happy path + edge cases + invalid input)
- `diff_minimalism`: Was the diff minimal? (1 = opportunistic refactoring, 5 = smallest possible change)

**reviewer**
- `false_positives`: How many findings did humans dismiss? (count)
- `false_negatives`: How many issues did humans catch that reviewer missed? (count)
- `actionable_feedback`: Were findings specific and fixable? (1 = vague, 5 = line references + corrected code)

**security**
- `findings_accuracy`: Were security findings valid? (1 = all false alarms, 5 = all real issues)
- `false_alarm_rate`: How many findings were dismissed? (count)

**test-writer**
- `edge_case_coverage`: Did tests cover edge cases? (1 = happy path only, 5 = comprehensive)
- `test_soundness`: Are tests well-structured? (1 = brittle/mocking everything, 5 = solid fixtures, observable behavior)

## When to score

Score at these points:
1. **After human review** — score planner, coder, reviewer, test-writer
2. **After security step** — score security (if step was run)
3. **After merge** — add `human_corrections` list

## How to use scores

### Per-feature (immediate)
- If any agent scores ≤ 2, note the pattern in the PR description
- If reviewer has 2+ false negatives, the review checklist may need updating

### Monthly (aggregate)
Run `python scripts/agent_report.py` to generate:
- Average scores per agent per dimension
- Trend over time (improving/declining)
- Top correction patterns (most common human fixes)
- Agents needing prompt updates

### Quarterly (act on patterns)
- If planner consistently misses migrations → update planner.md migration detection rules
- If reviewer has high false positives → tighten reviewer.md checklist
- If test-writer misses edge cases → add domain-specific test patterns

## File locations

| File | Purpose |
|------|---------|
| `.agents/memory/agent_scores.jsonl` | Append-only score log |
| `scripts/agent_report.py` | Monthly aggregation script |
| `.agents/skills/evaluation/SKILL.md` | This file |

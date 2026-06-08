> Load with: "metrics skill" in your prompt
> Example: "Use the metrics skill to implement this feature."

# Metrics Skill — prei

## Metrics tracked (DORA + AI economics)
| Metric | Target (Green) | Amber | Red |
|---|---:|---:|---:|
| Deployment frequency | >= 5/week | 2-4/week | <= 1/week |
| Lead time (issue->deploy) | < 3 days | 3-7 days | > 7 days |
| Change failure rate | < 5% | 5-15% | > 15% |
| Mean time to restore | < 4 hours | 4-24 hours | > 24 hours |
| Rework rate (14-day churn) | < 10% | 10-20% | > 20% |
| PR revision rate | < 25% | 25-40% | > 40% |
| AI credit burn rate | <= budget plan | +1-20% over | >20% over |

## Measurement commands
- Deployment frequency: `gh run list --workflow docker-publish.yml --limit 200 --json createdAt,conclusion`
- Lead time: `gh issue list --state all --limit 200 --json number,createdAt,closedAt`
- Change failure rate: `gh issue list --label incident --state all --limit 200 --json number,createdAt,closedAt`
- MTTR: `gh issue list --label incident --state all --limit 200 --json createdAt,closedAt`
- Rework rate baseline volume: `git log --since='30 days ago' --numstat --pretty=format:`
- Rework/rollback signals: `git log --since='30 days ago' --grep='revert\|rollback\|fix' --oneline`
- PR revision rate: `gh pr list --state closed --limit 200 --json number,reviewDecision,updatedAt`
- AI credit burn (manual dashboard export): `echo "Capture monthly credits from GitHub billing dashboard"`

## Rework rate formula
```
rework_rate = (lines_changed_within_14_days / total_lines_authored_in_period) * 100
```
Example commands:
```bash
git log --since='30 days ago' --numstat --pretty=format:
git log --since='30 days ago' --name-only --pretty=format:'%H %ad' --date=short
```
Use the first output for denominator and a 14-day churn sample for numerator.

## Monthly review ritual
1. Export prior-month GitHub billing and workflow data.
2. Compute all 7 metrics and set Green/Amber/Red status.
3. Compare AI credit burn against team budget target.
4. Identify top two regressions and assign owners.
5. Update `docs/METRICS.md` with actions and deadlines.
6. Review instruction-file size drift and run `scripts/token-audit.sh`.
7. Run `python scripts/agent_report.py --month YYYY-MM` for agent accuracy.
8. If any agent averages < 3, update the role prompt and note in PR.

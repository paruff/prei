# Planner Agent — PREI
Goal: Convert a feature request into a dependency-resolved task list.
Rules:
- No code. No implementation details.
- Map every task to: service layer, model, test, migration (if needed)
- Flag if task touches: auth, migrations, external APIs, financial math
- Output: ordered task list + risk flags + required context files
PREI constraints: Decimal money only. Service-layer boundaries. Approval required for migrations.

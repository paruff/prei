> Load with: "architecture skill" in your prompt
> Example: "Use the architecture skill to implement this feature."

# Architecture Skill — prei

## Layer structure diagram
```
core/api_views.py -> core/services/ -> core/models.py
                                -> investor_app/finance/utils.py
                                -> core/integrations/
templates/ <- Django views/context only
```

## Dependency direction rules
- Allowed: `views -> services -> (models, integrations, finance utils)`.
- Disallowed: `views -> integrations` direct calls.
- Disallowed: financial formulas in views/models/templates.
- Disallowed: Django ORM or settings imports inside `investor_app/finance/utils.py`.

## Hard architectural rules
1. `core/models.py`: ORM definitions only; no business logic or API calls.
2. `core/services/`: business logic orchestration and KPI composition.
3. `core/serializers.py`: input/output validation, including Decimal parsing.
4. `core/integrations/`: external source adapters only.

## What to read before writing code
- `core/models.py`
- `docs/ARCHITECTURE.md`
- `docs/API_SURFACE.md`
- `docs/KNOWN_LIMITATIONS.md`
- `docs/CHANGE_IMPACT_MAP.md`

## PR architecture checklist
- [ ] No financial math in views/models/templates.
- [ ] No external API calls from views; service+integration path used.
- [ ] Decimal-safe currency behavior preserved.
- [ ] No layer violation added (dependency direction unchanged).
- [ ] Co-change files from `docs/CHANGE_IMPACT_MAP.md` addressed.

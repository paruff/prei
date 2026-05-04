# Prompt Library — prei

> DORA AI Cap 2: Versioned task-specific prompts. Add a changelog entry when a prompt is updated.

-----

## TDD — New KPI Function (investor_app/finance/utils.py)

**Context:** `core/models.py`, `investor_app/finance/utils.py`, your failing test

```
Implement the KPI function {{FUNCTION_NAME}} in investor_app/finance/utils.py to make this failing test pass.

Rules:
- Pure function — no Django ORM, no DB access, no external calls
- Use Decimal for all currency inputs and outputs (not float)
- Convert to float only if passing to numpy-financial, then convert result back to Decimal
- Guard against: division by zero, negative values, zero purchase price
- Type hints required on all parameters and return value
- Google-style docstring with Args, Returns, Raises sections
- Handle boundary cases: noi=0, very large values, negative inputs

Failing test:
{{PASTE_TEST}}
```

**Red flags:** Uses `float` for currency → reject. No division-by-zero guard → reject. No type hints → reject.

-----

## TDD — New API View/Endpoint

**Context:** `core/models.py`, `core/serializers.py`, `core/services/`, failing test

```
Implement the DRF view {{VIEW_NAME}} in core/api_views.py to make this failing test pass.

Rules:
- Requires authentication (IsAuthenticated permission class)
- All queryset filtering scoped to request.user
- Business logic delegated to core/services/ — no logic inline in view
- Financial calculations via investor_app/finance/utils.py — never inline in view
- Input validated at serializer level before reaching view logic
- Decimal for all currency — no float in DB operations

Read core/models.py and docs/API_SURFACE.md first.

Failing test:
{{PASTE_TEST}}
```

-----

## Code Review

```
@review-agent Review this PR for the prei Django application.
Read .github/copilot-instructions.md and docs/ARCHITECTURE.md first.

Report in five categories:
1. ARCHITECTURE: Financial math in views/models, external API calls from views
2. SECURITY: Missing IsAuthenticated, missing user scope on querysets, hardcoded secrets, raw error responses
3. TYPES: Missing type hints, float used for currency
4. TESTS: Financial functions missing boundary tests (zero, negative, large values)
5. DUPLICATION: Logic duplicating investor_app/finance/utils.py or core/services/

For each finding: file, line, description, corrected code.
End with: "Ready for human review? YES / NO"
```

-----

## Financial Boundary Test Generator

```
Generate boundary tests for this financial function: {{FUNCTION_NAME}}

Required test cases:
1. Happy path: typical realistic values for a residential investment property
2. Zero NOI or income: should return 0 or documented behaviour, not crash
3. Zero purchase price: should raise ValueError with clear message
4. Negative inputs: should raise ValueError or return 0 per function contract
5. Very large values: $10M+ purchase price, ensure no overflow or precision loss
6. Decimal precision: result should be accurate to at least 4 decimal places

Function:
{{PASTE_FUNCTION}}

Use pytest. Use Decimal for all monetary inputs.
```

-----

## Debugging — Django Query Performance

```
This Django queryset is slow. Suggest optimisations.

Current query:
{{PASTE_QUERYSET}}

Context: called in {{VIEW_OR_SERVICE}}, returns approx {{N}} rows in production.

Check:
1. Missing select_related or prefetch_related for ForeignKey/ManyToMany
2. N+1 query pattern in the view or template
3. Missing database index on filter/order_by fields (check core/models.py)
4. Opportunity to use .values() or .only() to reduce data transfer

Suggest the optimised queryset and any migration needed for indexes.
```

-----

## Documentation — API Surface Entry (Python)

```
Generate a docs/API_SURFACE.md entry for this Python function.

Format exactly:
### module.function_name(params)
**Purpose:** [one sentence]
**Parameters:** [param: type — description per param]
**Returns:** [type — what it contains]
**Side effects:** [DB writes, external calls, or "None (pure function)"]
**Raises:** [exception type and when]
**Example:**
\`\`\`python
[usage example]
\`\`\`

Function:
{{PASTE_FUNCTION}}
```

-----

## Changelog

|Date   |Prompt Changed |Reason  |
|-------|---------------|--------|
|2026-03|Initial library|AIOPS-04|

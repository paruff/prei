# Product Spec — Investor Workflow Documentation

**Product**: prei
**Discovery Draft**: `docs/product/discovery-draft.md`
**Status**: Active

---

## Functional Requirements

### Workflow Overview

| ID | Requirement | Priority | Description |
|---|---|---|---|
| FR-1 | Workflow overview exists | High | `docs/explanation/investor-workflow.md` links all 4 stages (Growth Areas, Discovery, Screening, Underwriting) with navigation map |
| FR-2 | Cross-links to guides | High | Overview links to each how-to guide using relative paths |

### Growth Areas Documentation

| ID | Requirement | Priority | Description |
|---|---|---|---|
| FR-3 | Growth Areas how-to exists | High | `docs/how-to-guides/analyze-growth-areas.md` covers: prerequisites, Growth Explorer, running analysis, interpreting results, export |
| FR-4 | Table columns explained | High | Documented columns match template: Rank, City, Growth metrics, Composite Score, Confidence |
| FR-5 | Data sources documented | Medium | Census ACS, FRED, HUD FMR, GreatSchools listed with limitations |

### Discovery Documentation

| ID | Requirement | Priority | Description |
|---|---|---|---|
| FR-6 | Discovery how-to exists | High | `docs/how-to-guides/discover-properties.md` covers: prerequisites, source selection, running discovery, results |
| FR-7 | All source types documented | High | HUD REO, USDA REO, VRM, ATTOM, County all documented with rent data availability |
| FR-8 | Troubleshooting section | Medium | Common issues and resolutions documented |

### Screening Documentation

| ID | Requirement | Priority | Description |
|---|---|---|---|
| FR-9 | Screening how-to exists | High | `docs/how-to-guides/screen-properties.md` covers: criteria setup, hard/soft criteria, score interpretation, actions |
| FR-10 | Hard kill criteria documented | High | 4 criteria: state, property type, price range, foreclosure status |
| FR-11 | Soft criteria documented | High | 5 criteria with deduction logic: GACS, gross yield, price-to-rent, year built, beds |
| FR-12 | Rent data availability per source | Medium | VRM vs non-VRM screening differences explained |

### Underwriting Documentation

| ID | Requirement | Priority | Description |
|---|---|---|---|
| FR-13 | Underwriting how-to exists | High | `docs/how-to-guides/underwrite-deals.md` covers: pipeline underwriting vs BRRRR calculator |
| FR-14 | Pipeline metrics documented | High | GPR, EGI, OpEx, NOI, Cap Rate, CoC, MAO all explained |
| FR-15 | BRRRR inputs/outputs documented | High | All BRRRR calculator fields, verdicts, and DSCR warning explained |
| FR-16 | Comparison table included | Medium | Pipeline vs BRRRR differences clearly distinguished |

### UI Reference

| ID | Requirement | Priority | Description |
|---|---|---|---|
| FR-17 | UI patterns reference exists | Medium | `docs/reference/ui-patterns.md` documents design system, page layout, table patterns, form patterns |
| FR-18 | Accessibility documented | Medium | Semantic HTML, ARIA, focus states, color independence documented |

### Navigation & Cross-references

| ID | Requirement | Priority | Description |
|---|---|---|---|
| FR-19 | docs/index.md updated | High | New guides added to main docs index |
| FR-20 | All cross-references resolve | High | No broken relative links between guides |
| FR-21 | Consistent tone | Medium | All docs written for investors (not developers) |

---

## Non-Functional Requirements

| ID | Requirement | Priority | Description |
|---|---|---|---|
| NFR-1 | Accuracy | Critical | All documented behavior matches actual code/templates — code wins if they disagree |
| NFR-2 | Maintainability | Medium | Separate conceptual guides from implementation details |
| NFR-3 | Discoverability | Medium | Linked from main docs index and in-app where possible |

---

## Out of Scope

- API reference documentation (covered by `docs/API_SURFACE.md`)
- Deployment/ops guides (covered by `docs/DEPLOYMENT_STRATEGY.md`)
- Code architecture docs (covered by `docs/ARCHITECTURE.md`)
- Developer onboarding (covered by `docs/DEVEX_LOG.md`)
- Testing guides (covered by `docs/TEST_PYRAMID_PLAN.md`)

---

## How This Connects

| Doc | What it answers | Reference |
|---|---|---|
| `docs/product/discovery-draft.md` | What is the JTBD and riskiest assumption? | ↗ links up |
| `specification.md` | What is the active feature spec? | parallel |
| `design.md` | How is the feature implemented? | parallel |
| `tasks.json` | What are the task dependencies? | parallel |

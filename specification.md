# Specification: Comprehensive Documentation Review & Revision

**Feature**: Documentation overhaul for Growth Areas, Discovery, Screening, and Underwriting workflows
**Issue**: #335
**Status**: Draft

---

## User Intent

The user wants a comprehensive review and revision of documentation covering four core investor workflows:
1. **Growth Areas** — Market analysis and growth area identification
2. **Discovery** — Property sourcing from multiple data sources
3. **Screening** — Automated property evaluation against criteria
4. **Underwriting** — Financial analysis and deal evaluation

The documentation should be current, accurate, and improve the user experience (UX/UI perspective) for buy-and-hold real estate investors.

---

## Current State Assessment

### Existing Documentation Files

| Domain | Current Docs | Quality Notes |
|--------|--------------|---------------|
| **Growth Areas** | `docs/implementation-summary-growth-areas.md` (API spec), `docs/explanation/GACS_GUIDE.md` (conceptual guide), `docs/how-to-guides/` (missing growth areas guide) | API spec is detailed but implementation-focused; GACS guide is good but lacks UI flow context |
| **Discovery** | `docs/how-to-guides/import-data.md` (generic), `templates/property_discovery.html` (UI), view logic in `core/views/__init__.py:3450` | No dedicated discovery guide; UI flow not documented |
| **Screening** | `core/services/screening.py` (code has docstrings), `templates/pipeline/screener.html` (UI), view logic in `core/views/__init__.py:1898` | No user-facing documentation; complex logic not explained |
| **Underwriting** | `core/services/underwriting.py` (code has docstrings), `templates/brrrr_calculator.html` (UI) | No user-facing documentation; BRRRR calc is separate from pipeline underwriting |

### Gaps Identified

1. **No unified workflow documentation** — Users don't understand the end-to-end flow: Growth Areas → Discovery → Screening → Underwriting
2. **Missing how-to guides** for Growth Areas, Discovery, Screening, Underwriting
3. **UI/UX not documented** — Template structure, user journeys, navigation patterns
4. **API vs UI disconnect** — Implementation summary is API-focused, not user-journey focused
5. **Screening criteria configuration** — Not documented for users
5. **Underwriting solver usage** — Not explained in user terms (BRRRR vs pipeline underwriting)
6. **Data confidence & limitations** — Not prominently surfaced in UI docs

---

## Requirements

### Functional Requirements

| ID | Requirement | Priority | Description |
|----|-------------|----------|-------------|
| REQ-1 | **Workflow Overview Document** | High | Create a unified guide explaining the 4-stage investor workflow: Growth Areas → Discovery → Screening → Underwriting |
| REQ-2 | **Growth Areas Documentation** | High | Update/replace implementation summary with user-facing guide covering: GACS scoring, Growth Explorer UI, interpreting results, data confidence |
| REQ-3 | **Discovery Documentation** | High | Create how-to guide for property discovery: source selection, running discovery, understanding results, screening integration |
| REQ-4 | **Screening Documentation** | High | Create how-to guide for screening: criteria configuration, hard vs soft criteria, understanding pass/fail, re-screening |
| REQ-5 | **Underwriting Documentation** | High | Create how-to guide for underwriting: BRRRR calculator vs pipeline underwriting, input fields, interpreting metrics (NOI, Cap Rate, CoC, MAO), DSCR requirements |
| REQ-6 | **UX/UI Documentation** | Medium | Document template patterns, navigation flow, component library usage, accessibility considerations |
| REQ-7 | **Cross-references & Navigation** | Medium | Ensure all docs cross-link correctly; add to main index/README |
| REQ-8 | **Accuracy Review** | High | Verify all documented features match current implementation (code, templates, views) |

### Non-Functional Requirements

| ID | Requirement | Priority | Description |
|----|-------------|----------|-------------|
| NFR-1 | **Audience-appropriate tone** | High | Written for buy-and-hold investors (not developers); avoid implementation details unless relevant |
| NFR-2 | **Visual clarity** | Medium | Use tables, code blocks, callouts consistently; match existing design system |
| NFR-3 | **Accuracy** | Critical | All documented behavior must match actual code/templates |
| NFR-4 | **Discoverability** | Medium | Linked from main docs index, README, and in-app help where possible |
| NFR-5 | **Maintainability** | Medium | Separate conceptual guides from implementation details; use consistent structure |

---

## Acceptance Criteria

| ID | Criterion | Test Type | Reasoning |
|----|-----------|-----------|-----------|
| AC-1 | Workflow overview document exists and links to all 4 domain guides | unit (file exists) | Verifies structural completeness |
| AC-2 | Growth Areas guide explains GACS, Growth Explorer, data confidence, and links to API spec | live-system | Must verify UI matches documented behavior |
| AC-3 | Discovery guide covers source selection, running discovery, results interpretation, screening integration | live-system | End-to-end user flow verification |
| AC-4 | Screening guide covers criteria setup, hard/soft criteria, kill reasons, pass/fail logic, re-screen | live-system | Complex business logic verification |
| AC-5 | Underwriting guide distinguishes BRRRR calc from pipeline underwriting; explains all metrics | live-system | Financial accuracy critical |
| AC-6 | All documented UI elements (buttons, tables, chips, forms) match actual templates | live-system | UI accuracy verification |
| AC-7 | All cross-references resolve (no broken links) | unit | Link validation |
| AC-8 | No documented feature that doesn't exist in code | unit | Accuracy check against implementation |
| AC-9 | Data confidence/warnings prominently displayed in relevant guides | unit | Risk communication requirement |

---

## Constraints

1. **Stack**: Django templates, vanilla CSS (custom properties), no Bootstrap
2. **Design System**: Uses `tokens.css` + `base.css` — document component patterns
3. **Accuracy First**: If code and docs disagree, code wins — update docs to match
3. **No New Features**: This is documentation-only; no code changes unless fixing bugs found during review
4. **Governance**: Follow existing doc structure in `docs/` (how-to-guides/, explanation/, reference/, tutorials/)
5. **Links**: Use relative paths; ensure they work in GitHub Pages deployment

---

## Governance Alignment

- **Documentation Standards**: Follows `docs/FEATURE_SPEC_GUIDE.md` and `docs/DOCS_AUDIT.md`
- **Design System**: Uses existing CSS custom properties; no inline styles
- **Security**: No secrets in docs; no PII
- **Accessibility**: Document semantic HTML patterns used in templates

---

## Out of Scope

- API reference documentation (covered by `API_SURFACE.md`)
- Deployment/ops guides (covered by `DEPLOYMENT_STRATEGY.md`, `DEVEX_LOG.md`)
- Code architecture docs (covered by `ARCHITECTURE.md`)
- Developer onboarding (covered by `DEVEX_LOG.md`)
- Testing guides (covered by `TEST_PYRAMID_PLAN.md`)

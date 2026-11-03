# Specification: lease and keep it leased

**Status**: proposed (approved by merging the PR that changes this file)
**From**: [intent.md](intent.md) · **Plan**: [plan.md](plan.md) (goals G8–G12)
**Decisions**: all earlier decisions stand ([archived spec](features/functioning-prei/spec.md)). 2026-11-02: leasing is decision analytics, not property management; applicant data kept to the minimum; rent suggestion reuses the existing rent chain.
**IDs**: continue from the archived spec (FR-18, NFR-7, AC-19). IDs are never reused. Requirements still marked Later in the archived spec keep their IDs and appear in plan.md "Later".

---

## Current State Assessment

Audit of 2026-11-02 (code, running container, live site).

| Gap | Current | Where |
|---|---|---|
| **Lease → portfolio** | A signed lease writes `monthly_rent` on the leasing record only; no `RentalIncome` is created | `core/views/leasing.py` `leasing_lease` |
| **Stage integrity** | Each stage view sets its stage unconditionally (an Approved listing can be sent back to Showing); the kanban jumps forward with no data; stage logic in views duplicates the service | `core/views/leasing.py`, `core/services/leasing.py` |
| **Input validation** | Raw `request.POST`; `Decimal("")` or `"1,800"` → 500; lease end date not checked against start | `leasing_lease`, `leasing_add` |
| **Stage history** | Built as `(stage, None)`: no dates are stored | `leasing_detail` |
| **Stage order** | Copied in four places | service, list, kanban, detail |
| **Applicants** | One name per listing, overwritten by the next application; screening is a pass/fail box and a note | `LeasingPipelineProperty` |
| **Hold / withdraw** | `put_on_hold` and `mark_filled` are never called; no UI | `core/services/leasing.py` |
| **Decision support** | No suggested rent, no vacancy cost, days vacant shown only at the Listing stage | list, add, kanban |
| **After move-in** | No lease end view, renewal or turnover; the banner sends renewals to Portfolio, which has none (LIMIT-14) | `templates/leasing/leasing_list.html` |
| **Units** | One leasing record per property; `Property.units` ignored | model |
| **Tests** | Acceptance checks only that the pages return 200; the journey checks "stabilized" only | `tests/acceptance/test_leasing.py`, `tests_bdd/` |
| **Hosting** | Render returns 404; only the docs site is live | `render.yaml` |

---

## Requirements

### Functional Requirements

| ID | Requirement | Priority | Goal | Description |
|---|---|---|---|---|
| FR-19 | **One lease, one record** | Critical | G8 | Stages advance only forward, one at a time, through the service; a stage cannot be entered without its data (Application: an applicant; Lease Signed: rent, start date, end date after start; Move-In: date). On hold and withdrawn are reachable from the UI |
| FR-20 | **Stage history** | High | G8 | Every stage change is stored with its date; the detail page shows real dates and days spent per stage |
| FR-21 | **Lease feeds the portfolio** | Critical | G8 | Signing a lease creates the property's `RentalIncome` from the lease start date; portfolio cash flow and actuals-vs-pro-forma use it; no rent is typed twice |
| FR-22 | **Validated leasing forms** | Critical | G8 | Every leasing POST goes through a Django form; bad input re-renders with a field error, never a 500 |
| FR-23 | **Unit-aware leasing** | High | G8 | A leasing record carries a unit label when `Property.units > 1`; each unit has at most one active listing and one current lease |
| FR-24 | **Suggested rent** | High | G9 | Listing a unit shows a suggested rent from the existing rent chain, with its source and confidence; the asking rent is compared to it |
| FR-25 | **Cost of vacancy** | High | G9 | Each vacant unit shows days vacant (from vacancy start to move-in, not only while Listed) and cost so far: daily rent plus daily carrying costs |
| FR-26 | **Many applicants per listing** | Critical | G9 | A listing holds any number of applicants, each with minimal data (intent constraints), a status and a decision reason; approving one closes the others with a reason |
| FR-27 | **Written screening criteria** | High | G9 | The investor writes leasing criteria once (minimum income as a multiple of rent, minimum credit score, eviction and criminal look-back as the investor's own rules). Each applicant is scored against them the same way; the criteria version in force is stored with each decision |
| FR-28 | **Listing health prompt** | Medium | G9 | A listing with no application after a set number of days or showings shows a price-review prompt with the vacancy cost to date |
| FR-29 | **Lease end view** | High | G11 | Leases ending within 90, 60 and 30 days are listed on Leasing and flagged on the portfolio dashboard |
| FR-30 | **Renew or turn over** | High | G11 | For a lease nearing its end, compare renewal (rent change, any concession) against turnover (expected vacancy days × daily rent, make-ready, leasing fee) over the next term; show the break-even rent increase |
| FR-31 | **Renewal and turnover actions** | High | G11 | Renewing creates the next lease and its `RentalIncome`; turnover reopens a listing pre-filled from the last lease and starts the vacancy clock at move-out |
| FR-32 | **Leasing KPIs** | High | G11 | Per property and for the portfolio: economic occupancy, average days vacant, days to lease, showing-to-application conversion, rent vs suggested rent, turnover rate |
| FR-33 | **Hosted** | Critical | G10 | prei runs on a hosted URL with Postgres, HTTPS and secrets from the environment; the database has scheduled backups and a restore has been tested; no WARN-level ZAP findings on the hosted URL (LIMIT-23) |
| FR-34 | **Provider tenant screening** | High | G12 | From an applicant record the investor requests a paid screening report; the provider collects consent, SSN and date of birth from the applicant directly; prei stores the result summary, report date, provider reference and fee, and checks the result against the written criteria (FR-27) |
| FR-1 to FR-5, FR-7, FR-9 | As in the archived spec | Later | Later | Rentcast, ATTOM rent, GACS backtest and signals, crime data, async work, CSP/SRI |

### Non-Functional Requirements

| ID | Requirement | Priority | Goal | Description |
|---|---|---|---|---|
| NFR-8 | **Applicant data minimal** | Critical | G9 | No SSN, date of birth, credit report file or protected-class field exists on any model; a test fails if one is added |
| NFR-9 | **Leasing math tested** | Critical | G9, G11 | Vacancy cost, renewal-vs-turnover and KPIs are service functions with Decimal unit tests, including zero rent, missing carrying costs and leases shorter than a month |
| NFR-10 | **No 5xx on leasing** | Critical | G8 | Leasing routes return non-5xx for blank, malformed and out-of-order input |
| NFR-11 | **No consumer report stored** | Critical | G12 | prei never receives or stores the full report, SSN or date of birth; provider callbacks are verified (signature or shared secret) and the API key comes from the environment |
| NFR-6 | **Zero-downtime deploy** | High | G10 | Kept from the archived spec; deploys run migrations before the new release takes traffic |
| NFR-1 to NFR-5 | As in the archived spec | Later | Later | |

---

## Acceptance Criteria

| ID | Criterion | Test Type | Goal |
|---|---|---|---|
| AC-20 | The journey signs a lease at 1800 and the portfolio shows 1800 as the property's rent and uses it in cash flow, with no rent entered in Portfolio | acceptance (container) | G8 |
| AC-21 | Moving a listing backwards, skipping a stage, or signing without rent/dates is refused with a message; blank and `1,800` rent give a field error, not a 500 | acceptance (container) | G8 |
| AC-22 | The detail page shows a stored date for every stage reached | acceptance (container) | G8 |
| AC-23 | The journey adds two applicants, one fails the written income criterion with its reason recorded, the other is approved, and the first keeps its record | acceptance (container) | G9 |
| AC-24 | The listing shows a suggested rent with its source, and days vacant and vacancy cost that match the service's unit-tested values | acceptance (container) | G9 |
| AC-25 | A model-field check finds no restricted applicant field (NFR-8) | unit | G9 |
| AC-26 | The journey sees the lease in the 90-day list, compares renew vs turn over, renews, and the portfolio shows the new rent from the renewal date | acceptance (container) | G11 |
| AC-27 | A turnover reopens a listing pre-filled from the last lease, and KPIs show the vacancy | acceptance (container) | G11 |
| AC-28 | `tests/acceptance/` and the journey pass with `BASE_URL` set to the hosted URL; a restore of last night's backup into a scratch database succeeds | live-system (hosted) | G10 |
| AC-29 | Against the provider's sandbox (or a recorded fake in CI), a screening request for an applicant returns a result that is stored as a summary and checked against the written criteria, with no restricted field stored | acceptance | G12 |
| AC-1 to AC-9 | As in the archived spec | as before | Later |

---

## Constraints

1. **Decimal money**; all leasing math in `core/services/`.
2. **Service-layer boundaries**: views call `core/services/leasing.py`; no stage logic in views.
3. **One stage order**: the `Stage` enum; no copies.
4. **Migrations need approval** (`migration-safety` skill); new models are additive.
5. **Design system**: existing partials and classes (DESIGN.md); no new colours.
6. **Free data**: the existing rent chain only; the screening provider (G12) is the one paid exception.
7. **External calls**: the screening adapter lives in `core/integrations/`; views never call it directly.

---

## Out of Scope

- Listing syndication, online application forms for tenants, e-signature, rent collection, maintenance, tenant portal (VISION non-goal: property management)
- Lease documents and adverse-action notices (no legal advice)
- Team sharing (#371, #372)

---

## Governance Alignment

- **KNOWN_LIMITATIONS.md**: G8–G11 resolve LIMIT-14; update its text when G11 lands.
- **CHANGE_IMPACT_MAP.md**: add leasing ↔ `RentalIncome` ↔ portfolio when G8 lands.
- **ARCHITECTURE.md**: no new layer; leasing follows the pipeline service pattern.

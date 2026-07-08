# Discovery Brief: PREI Full Acquisition & Leasing Pipeline
# Written: 2026-07-07 session with paruff
# Status: Ready for implementation via opencode / DeepSeek

---

## 1. What We Are Building

A CRM-like property acquisition and leasing pipeline that tracks individual
properties as they move through stages from discovery to stabilized cashflow.

This is the structural backbone of PREI as a product. Every other feature
(GACS, VRM, underwriting, portfolio) becomes a stage or data input in this
pipeline rather than a standalone tool.

---

## 2. The Problem Being Solved

### Current state (verified from codebase)
- PREI has underwriting math, portfolio tracking, and VRM discovery
- These are disconnected tools — no model links them into a workflow
- A user cannot see "here are 47 properties I am tracking, here is where
  each one is in my process, here is why I killed the other 200"
- There is no screening stage — properties go from discovery directly to
  underwriting, which is expensive (analyst time) and unscalable

### What institutional operators do differently
Properties move left → right through stages only when they pass criteria.
Most properties are killed early and cheaply. Only viable deals reach
expensive stages (underwriting, offer, due diligence).

### The gap this creates for prei users
Without a pipeline model, a user:
- Has no deal flow visibility
- Cannot track why they passed on a property
- Cannot see how many properties they screened vs underwrote vs offered on
- Cannot manage multiple properties at different stages simultaneously

---

## 3. Persona

**Primary:** Individual buy-and-hold investor, learning the craft, managing
deal flow solo or with a small team. Not institutional — does not have
a dedicated analyst. Time is the binding constraint.

**Jobs to be done:**
- "Show me which properties deserve my attention today"
- "Tell me why I should not waste time on this property"
- "Track where every deal I am looking at currently stands"
- "Show me my historical kill rate and why I passed on deals"
- "When a property I am watching hits my criteria, alert me"

---

## 4. Riskiest Assumptions

1. Users will actually move properties through pipeline stages manually
   (vs. expecting automation). Mitigation: make stage advancement one click;
   pre-fill as much as possible from source data.

2. A single PipelineProperty model can accommodate all source types
   (VRM, HUD, county, bank REO, etc.) without becoming unwieldy.
   Mitigation: generic source linkage pattern (source_type + source_id).

3. The leasing pipeline (tenant acquisition) is structurally similar enough
   to the acquisition pipeline to share UI patterns. To be validated in
   design phase.

---

## 5. What Is In Scope (this plan)

### Acquisition Pipeline (stages 1–8)
1. Market Selection — GACS (exists, being improved)
2. Property Discovery — multi-source inventory (VRM exists; others planned)
3. Property Screening — NEW: fast filter engine
4. Underwriting — exists, needs pipeline linkage
5. Offer Strategy — NEW: offer tracking
6. Due Diligence — NEW: DD checklist and status
7. Acquisition / Closing — NEW: closing record
8. Renovation / Turnover — NEW: rehab tracking

### Leasing Pipeline (stages 1–5)
1. Listing (property is rent-ready)
2. Applicant Discovery (where are leads coming from)
3. Applicant Screening (basic criteria)
4. Lease Execution
5. Move-in / Stabilized

### Navigation (confirmed by paruff)
```
Growth Areas | Purchase Pipeline | Portfolio | Leasing Pipeline
```
With submenus supporting sub-elements of each phase.

---

## 6. What Is NOT In Scope (this plan)

- AuctionAlert wiring to PipelineProperty — backlog per paruff
- Automated property discovery (no scraping in this plan — manual add or
  import from existing sources)
- MLS / IDX integration — deferred
- Celery / background jobs — deferred (alpha constraint)
- Multi-user team pipeline sharing — deferred (TeamMember model exists
  but pipeline sharing is post-alpha)
- Offer negotiation history beyond basic tracking
- Legal document storage
- Contractor management (beyond basic rehab budget fields)

---

## 7. Success Criteria

- A user can add a VrmProperty or ForeclosureProperty to their pipeline
  in one click and see it appear in their Purchase Pipeline view
- A user can advance a property through pipeline stages and record why
  they killed it at any stage
- The screening stage eliminates properties automatically based on
  user-configured thresholds before underwriting is triggered
- A user can see a kanban or list view of all active pipeline properties
  grouped by stage
- The leasing pipeline tracks a property from rent-ready to stabilized
- Nav reflects the four top-level sections with correct submenus

---

## 8. DORA Mapping

- Deployment Frequency: pipeline is additive — no existing endpoints broken
- Lead Time: estimated 6–8 tasks per pipeline phase; plan below
- Change Failure Rate: migration-heavy — each new model needs paruff review
- MTTR: all new models are nullable/additive; rollback is safe

---

## 9. Prior Art in This Codebase

| Model | Role in Pipeline |
|---|---|
| GrowthArea | Stage 1 output — market selection |
| VrmProperty | Stage 2 source — discovery |
| ForeclosureProperty | Stage 2 source — discovery (multi-source ready) |
| Listing | Stage 2 source — normalized listing |
| InvestmentAnalysis | Stage 4 output — underwriting results |
| Property | Post-acquisition record — Stage 7 output |
| MonthlyActuals | Post-stabilization — portfolio tracking |
| UserWatchlist | Links user to ForeclosureProperty — to be superseded by PipelineProperty |

---

## 10. Open Questions (resolved before implementation)

| # | Question | Answer |
|---|---|---|
| Q1 | PipelineProperty or stage fields on existing models? | PipelineProperty — confirmed by paruff |
| Q2 | Generic FK or source_type+source_id for linking sources? | source_type + source_id pattern — safer, no GenericForeignKey complexity |
| Q3 | AuctionAlert wired to pipeline? | Backlog — confirmed by paruff |
| Q4 | Leasing pipeline definition? | Tenant acquisition: listing → applicant → screening → lease → move-in |
| Q5 | Nav structure? | Growth Areas / Purchase Pipeline / Portfolio / Leasing Pipeline |

Senior PM Critique: prei — Passive Residential Real Estate Investing Tool
TL;DR Verdict
The engineering foundation is solid. The architecture is clean, the tooling choices are professional, and the AI-assisted workflow is genuinely ahead of most solo/small-team projects. But the product roadmap is engineering-led, not investor-outcome-led. A top .01% passive RE investor would close this tab after 90 seconds because the core use cases don't match how passive residential investing actually works. Here's the full breakdown.

1. You're Building for the Wrong Investor
The critical problem: The product is heavily oriented around foreclosures and auction monitoring (WebSocket live updates, auction reminders, 15-minute status checks, Celery beat, watchlists for distressed properties). Foreclosure/auction investing is not passive investing — it is one of the most active, operationally demanding strategies in real estate.

Passive residential RE investing means:

Buy-and-hold SFR (single-family rental) or small multifamily (2–4 units)
Turnkey properties from providers in landlord-friendly markets
Build-to-rent
DST (Delaware Statutory Trust) or syndications as a limited partner
None of those are in the roadmap. What's in the roadmap is an active deal-hunter's tool that happens to calculate cap rate.

Fix: Reframe Phase 1 entirely around the passive investor's primary workflow: "I found a rental property. Help me decide if I should buy it and at what price."

2. The Scoring Model Is a Placeholder, Not a Feature
score_listing_v1 combines price-per-square-foot and freshness. This would be embarrassing to show a passive investor. The metrics that actually drive a buy/no-buy decision for buy-and-hold:

1% Rule (monthly rent ≥ 1% of purchase price) — instant filter, must be the first screen
GRM (Gross Rent Multiplier) — fast market-level comparison
Rent-to-price ratio adjusted for market (coastal vs Midwest)
Cap rate vs. local market cap rate — is this above or below the prevailing market rate?
Projected cash-on-cash in years 1, 3, 5 under conservative assumptions
Replace score_listing_v1 with a multi-signal underwriting score that actually reflects passive investing logic.

3. The Biggest Missing Feature: Tax Benefits
This is the single biggest gap and a dealbreaker for sophisticated passive investors. The IRS treats rental real estate with extraordinary generosity, and that's a major reason people invest in it over equities. None of this is modeled:

Depreciation: 27.5-year straight-line on residential. For a $300K property with $50K land value, that's ~$9,100/year in paper loss — on a cash-flowing property. This alone can shelter $9K of other income.
Cost segregation: Accelerate depreciation on personal property and land improvements. A $400K purchase could yield $40–80K of year-1 deductions. This is what the top .01% use as their primary tax weapon.
Passive activity loss (PAL) rules: The $25K allowance for active participants earning under $100K, phase-out up to $150K. High earners use REPS (Real Estate Professional Status) or short-term rental strategies to unlock unlimited losses. If you're not modeling this, you're not modeling passive RE.
QBI (Section 199A): Potentially 20% deduction on qualified rental income.
1031 exchange planning: When to sell, what to roll into, time constraints, qualified intermediary requirements.
Bonus depreciation (post-TCJA): Currently phasing down — tracking what year applies matters.
After-tax IRR vs. pre-tax IRR: The current irr() function returns pre-tax. That's almost useless for comparing RE vs. stock portfolio returns without tax adjustment.
Recommendation: Add a tax_analysis module to finance/utils.py starting with depreciation schedule and after-tax cash flow. This moves the needle more than any Phase 3–5 feature.

4. Missing: Hold Period & Exit Analysis
Every passive investor thinks in 5/7/10-year windows. The current model is essentially static (calculate today's metrics). What's needed:

Year-by-year projection: rent growth (3–4%/yr typical), expense growth (inflation), mortgage amortization schedule, equity build-up
Appreciation modeling: conservative/base/optimistic scenarios (0%, 3%, 5% annual)
Sale proceeds calculator: At year 7, if I sell, what's net after: agent commissions (5–6%), closing costs (~1%), capital gains tax (federal + state), depreciation recapture (25% on accumulated depreciation)
Total return: Cash flow PV + equity at exit + appreciation = total ROI vs. alternative investment
This is the model that serious investors build in Excel. You're building the thing that should replace that Excel sheet — but it has to be at least as good.

5. Missing: BRRRR Strategy Support
BRRRR (Buy, Rehab, Rent, Refinance, Repeat) is the dominant strategy among wealth-building passive investors. It's how people go from 1 property to 10 properties with limited capital. It requires:

ARV (After-Repair Value) estimation from comps
Rehab cost estimator (rough $/sq ft by renovation level: cosmetic, moderate, full gut)
Post-rehab DSCR refinance analysis: What loan can I get at 75% LTV of ARV?
Cash-out calculation: How much capital can I recycle into the next deal?
Deal quality metric: Did I leave any of my own money in the deal? (Infinite CoC scenario)
6. Missing: Market Selection Intelligence
The top .01% investors don't just analyze properties — they select markets first, then find properties. A market that has declining population, one major employer, and a tenant-friendly eviction process will destroy returns regardless of how good the numbers look on paper. The tool needs:

Price-to-rent ratio by metro (Zillow, Census data — public)
Population growth / net migration (Census Bureau — public)
Employment diversity score (BLS data — public, free)
Landlord-friendliness index (eviction timeline, rent control laws by state)
Rent growth rate by ZIP or metro (Rentcast, ApartmentList — affordable APIs)
Days-on-market trend for the investor segment (distressed vs retail)
The current MarketSnapshot model has crime_score and school_rating — useful, but those are tenant-attractiveness metrics. You need investor-viability metrics.

7. Missing: Financing Structure Comparison
Passive investors frequently model multiple financing structures before buying:

Conventional 20% down vs. 25% down (rate differential, PMI elimination)
30-year fixed vs. ARM (5/1 ARM if holding <7 years)
Portfolio loan vs. Fannie/Freddie (LLC ownership, non-QM considerations)
Cash purchase vs. leveraged: IRR comparison (leverage amplifies both gains and losses)
Seller financing scenarios: Interest-only, balloon payments, wrap mortgages
HELOC tap-and-return strategy: Using existing home equity to fund down payment
The calculate_monthly_mortgage() function exists, which is a start. Build the comparison UI around it.

8. What the Roadmap Gets Right (Credit Where Due)
CMA engine: Correct and important — finding undervalued properties vs. comps is core to passive buying discipline.
Portfolio aggregation (portfolio.py): Essential for an investor with 3+ properties.
Decimal precision throughout: This is actually rare and commendable. Most hobby projects use floats and get burned.
Architecture separation: finance/utils.py as pure functions is the right call. (Note: it currently imports from core.models — that's a violation of your own rule and needs fixing.)
Phase 4.1 Scenario Modeling: High value, correctly prioritized.
Structured logging: Right instinct.
Team collaboration (Phase 4.3): Spouses, partners, and deal partners reviewing the same analysis is a real workflow.
9. Roadmap Priority Inversion Issues
Current Priority	Should Be	Why
Phase 1: Auction/foreclosure scanning	Phase 3+	Not passive; narrow market
Phase 2: Market snapshots	Phase 1	Critical for buy decision
Phase 3: Recommendations engine	Phase 2+	Needs market data foundation first
Phase 5: Mobile push for auctions	Cut or last	Wrong use case for passive investors
Phase 5.2: Marketplace	Cut from core	Feature creep; separate product
Not in plan: Depreciation/tax modeling	Phase 1	The #1 reason people invest in RE
Not in plan: Hold period projections	Phase 1	Every investor models this
Not in plan: BRRRR analysis	Phase 2	Most popular wealth-building strategy
Not in plan: Market selection scoring	Phase 2	Market first, deal second
Not in plan: After-tax IRR	Phase 1	Pre-tax IRR is incomplete
10. Technical Gaps That Will Hurt You
finance/utils.py violates its own contract: It imports from core.models import InvestmentAnalysis, Listing, Property. Pure functions should have zero Django imports. This makes the module untestable in isolation and is specifically against your architecture rules.

KNOWN_LIMITATIONS.md is a placeholder: It lists [LIMIT-01] [PLACEHOLDER]. This file is supposed to be read before every AI session. It's currently noise.

API_SURFACE.md services section is a placeholder: [service_module].[function_name](params) — the most important part of the context file for AI agents is empty.

estimate_insurance() hardcodes a $1200 national average: Insurance is highly geographic. Florida vs. Ohio vs. California are 3–10x different. This will produce dangerously wrong numbers for a user making a real decision.

InvestmentAnalysis is a snapshot, not a history: The model stores a single set of KPIs per property with updated_at. You lose all analytical history. A time-series of analysis snapshots is much more valuable for passive investors who want to see how a property's performance has trended.

No loan model: There's no Loan model in core/models.py. Mortgages aren't tracked. This means refinancing scenarios, amortization schedules, and equity calculations all have to be passed in manually every time. This is a fundamental data model gap.

Listing.SOURCE_CHOICES only has ("dummy", "Dummy"), ("external", "External"): This is pure scaffold. You need real source taxonomy: MLS, Zillow, Redfin, ATTOM, HUD, turnkey_provider, off_market, etc.

11. What Would the Top .01% Think?
They would recognize the engineering quality (clean architecture, proper decimal math, well-structured CI) as better than 90% of internal tools they've seen. But they would immediately ask:

"Why is this spending so much time on auction alerts? Where's my depreciation schedule? Where's my hold-period exit analysis? Can it handle a portfolio of 15 properties across 4 states with 3 different LLCs? Where's my after-tax total return?"

The people at that level are using Argus Enterprise, RealPage, or custom Excel models built by financial analysts. To compete with or replace those tools, you need to lead with the financial modeling depth, not the data sourcing. Data is a commodity. Institutional-quality financial analysis for individual investors is the actual value proposition.

Suggested Revised Roadmap Headline
Phase 1 — The Underwriting Engine: Property input → full financial model (NOI, CoC, Cap Rate, DSCR, depreciation, after-tax cash flow, hold-period projection) → buy/no-buy recommendation. One property, one user, no integrations needed.

Phase 2 — Market Intelligence: Price-to-rent ratios, market scoring, rent comps, market selection tools. Make the engine work with real data.

Phase 3 — Portfolio Tracking: Multi-property, time-series performance, BRRRR tracking, refinance logging, equity dashboard.

Phase 4 — Automation & Scale: Listing scanning, deal scoring, saved searches, alerts. Now the funnel makes sense because the analysis engine is proven.

Phase 5 — Collaboration & Integration: Team access, CRM, exports, API, mobile.

You asked
best way to share response with contributors


Implementing a response sharing method for contributors

55s

Setting up environment

Start agent firewall

Clone repository paruff/prei

Start 'github-mcp-server' MCP server

Start 'playwright' MCP server
1 premium request · Claude Sonnet 4.6
The best way depends on the audience and desired outcome. Here are the options ranked for this specific repo and use case:

Option 1 (Recommended): GitHub Issue labeled strategy or product
Best for: Driving action. Contributors can comment, reference it from PRs, and individual items can be converted into child issues.

Create a single GitHub Issue titled something like:

Product Strategy Review: Passive Investing Focus & Roadmap Gaps

Paste the critique as the body. Then:

Label it strategy, product, or roadmap
Pin it to the repo (Settings → Pin issue)
Reference it from the relevant open phase issues (e.g., "This issue was raised in #XX — tax modeling should precede auction features")
Advantage: Permanent, searchable, linkable from code and PRs, threaded discussion, actionable.

Option 2: docs/PRODUCT_STRATEGY.md committed to main
Best for: Making it part of the permanent agent context (since docs/ files are loaded before every Copilot session per your AGENTS.md).

The critique covers things like the finance/utils.py architecture violation and missing financial models that every future agent session should know about. Committing it to docs/ means AI agents will read it.

Option 3: GitHub Discussion
Best for: If the repo has Discussions enabled and you want a more open-ended conversation before converting anything to issues. Less structured than issues but good for async brainstorming.

Recommended combined approach:
Commit docs/PRODUCT_STRATEGY.md — the full critique becomes permanent context for agents and contributors reading the docs.
Open one tracking issue (Product Strategy Pivot: Passive Investing Core) that summarizes the top 5 gaps and links to the doc. Pin it.
Edit the existing phase issues (particularly Phase 1–2) with a reference to the tracking issue so contributors understand the context when they pick up work.
Would you like me to create the docs/PRODUCT_STRATEGY.md file and/or open the tracking issue now?

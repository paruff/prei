"""Tests verifying documentation completeness per design.md.

These tests validate that each investor-workflow doc file:
1. Exists at the expected path
2. Contains all required sections per design.md
3. Has cross-references that resolve
"""

import pathlib


DOCS = pathlib.Path(__file__).resolve().parent.parent / "docs"


def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# investor-workflow.md
# ---------------------------------------------------------------------------

INVESTOR_WORKFLOW = DOCS / "explanation" / "investor-workflow.md"


class TestInvestorWorkflow:
    def test_file_exists(self):
        assert INVESTOR_WORKFLOW.exists(), f"{INVESTOR_WORKFLOW} missing"

    def test_has_overview_section(self):
        content = _read(INVESTOR_WORKFLOW)
        assert "## Overview" in content

    def test_has_all_four_stages(self):
        content = _read(INVESTOR_WORKFLOW)
        for stage in [
            "Stage 1: Growth Areas",
            "Stage 2: Discovery",
            "Stage 3: Screening",
            "Stage 4: Underwriting",
        ]:
            assert stage in content, f"Missing section: {stage}"

    def test_links_to_all_four_howto_guides(self):
        content = _read(INVESTOR_WORKFLOW)
        for guide in [
            "analyze-growth-areas.md",
            "discover-properties.md",
            "screen-properties.md",
            "underwrite-deals.md",
        ]:
            assert guide in content, f"Missing link to {guide}"

    def test_has_navigation_map(self):
        content = _read(INVESTOR_WORKFLOW)
        assert "Navigation Map" in content

    def test_mentions_gacs(self):
        content = _read(INVESTOR_WORKFLOW)
        assert "GACS" in content

    def test_mentions_data_confidence(self):
        content = _read(INVESTOR_WORKFLOW)
        assert "confidence" in content.lower()


# ---------------------------------------------------------------------------
# analyze-growth-areas.md
# ---------------------------------------------------------------------------

GROWTH_AREAS = DOCS / "how-to-guides" / "analyze-growth-areas.md"


class TestAnalyzeGrowthAreas:
    def test_file_exists(self):
        assert GROWTH_AREAS.exists(), f"{GROWTH_AREAS} missing"

    def test_has_prerequisites(self):
        content = _read(GROWTH_AREAS)
        assert "## Prerequisites" in content

    def test_has_step_by_step(self):
        content = _read(GROWTH_AREAS)
        for step in ["Step 1", "Step 2", "Step 3", "Step 4"]:
            assert step in content, f"Missing {step}"

    def test_mentions_fred_api_key(self):
        content = _read(GROWTH_AREAS)
        assert "FRED_API_KEY" in content

    def test_mentions_hud_api_key(self):
        content = _read(GROWTH_AREAS)
        assert "HUD_API_KEY" in content

    def test_has_table_columns_explained(self):
        content = _read(GROWTH_AREAS)
        assert "Composite Score" in content
        assert "Confidence" in content

    def test_has_confidence_chips(self):
        content = _read(GROWTH_AREAS)
        assert "chip" in content.lower() or "≥ 80%" in content

    def test_has_gacs_understanding(self):
        content = _read(GROWTH_AREAS)
        assert "Understanding GACS" in content

    def test_has_data_sources_section(self):
        content = _read(GROWTH_AREAS)
        assert "Data Sources" in content or "Limitations" in content

    def test_has_troubleshooting(self):
        content = _read(GROWTH_AREAS)
        assert "Troubleshooting" in content

    def test_links_to_discover_properties(self):
        content = _read(GROWTH_AREAS)
        assert "discover-properties.md" in content

    def test_links_to_screen_properties(self):
        content = _read(GROWTH_AREAS)
        assert "screen-properties.md" in content

    def test_links_to_gacs_guide(self):
        content = _read(GROWTH_AREAS)
        assert "GACS_GUIDE.md" in content


# ---------------------------------------------------------------------------
# discover-properties.md
# ---------------------------------------------------------------------------

DISCOVER = DOCS / "how-to-guides" / "discover-properties.md"


class TestDiscoverProperties:
    def test_file_exists(self):
        assert DISCOVER.exists(), f"{DISCOVER} missing"

    def test_has_prerequisites(self):
        content = _read(DISCOVER)
        assert "## Prerequisites" in content

    def test_has_step_by_step(self):
        content = _read(DISCOVER)
        for step in ["Step 1", "Step 2", "Step 3", "Step 4"]:
            assert step in content, f"Missing {step}"

    def test_documents_all_five_sources(self):
        content = _read(DISCOVER)
        for source in ["HUD REO", "USDA REO", "VRM", "ATTOM", "County"]:
            assert source in content, f"Missing source: {source}"

    def test_has_source_details_section(self):
        content = _read(DISCOVER)
        assert "Source Details" in content

    def test_mentions_rent_data_availability(self):
        content = _read(DISCOVER)
        assert "rent data" in content.lower() or "rent estimate" in content.lower()

    def test_has_kpi_cards(self):
        content = _read(DISCOVER)
        assert "KPI" in content

    def test_has_troubleshooting(self):
        content = _read(DISCOVER)
        assert "Troubleshooting" in content

    def test_links_to_screen_properties(self):
        content = _read(DISCOVER)
        assert "screen-properties.md" in content


# ---------------------------------------------------------------------------
# screen-properties.md
# ---------------------------------------------------------------------------

SCREEN = DOCS / "how-to-guides" / "screen-properties.md"


class TestScreenProperties:
    def test_file_exists(self):
        assert SCREEN.exists(), f"{SCREEN} missing"

    def test_has_prerequisites(self):
        content = _read(SCREEN)
        assert "## Prerequisites" in content

    def test_has_step_by_step(self):
        content = _read(SCREEN)
        for step in ["Step 1", "Step 2", "Step 3"]:
            assert step in content, f"Missing {step}"

    def test_documents_hard_kill_criteria(self):
        content = _read(SCREEN)
        assert "Hard Kill" in content or "hard kill" in content.lower()
        for crit in ["state", "property type", "price", "foreclosure"]:
            assert crit in content.lower(), f"Missing hard criterion: {crit}"

    def test_documents_soft_criteria(self):
        content = _read(SCREEN)
        assert "Soft" in content
        for crit in [
            "GACS",
            "gross yield",
            "price-to-rent",
            "year built",
            "beds",
        ]:
            assert crit.lower() in content.lower(), f"Missing soft criterion: {crit}"

    def test_has_score_interpretation(self):
        content = _read(SCREEN)
        assert (
            "Score Interpretation" in content
            or "score interpretation" in content.lower()
        )
        assert "≥ 50" in content
        assert "0" in content

    def test_has_actions_section(self):
        content = _read(SCREEN)
        assert "## Actions" in content
        assert "Underwriting" in content
        assert "Kill" in content
        assert "Re-Screen" in content

    def test_has_common_questions(self):
        content = _read(SCREEN)
        assert "Common Questions" in content

    def test_documents_rent_data_availability(self):
        content = _read(SCREEN)
        assert "Rent Data" in content or "rent data" in content.lower()

    def test_links_to_underwrite_deals(self):
        content = _read(SCREEN)
        assert "underwrite-deals.md" in content


# ---------------------------------------------------------------------------
# underwrite-deals.md
# ---------------------------------------------------------------------------

UNDERWRITE = DOCS / "how-to-guides" / "underwrite-deals.md"


class TestUnderwriteDeals:
    def test_file_exists(self):
        assert UNDERWRITE.exists(), f"{UNDERWRITE} missing"

    def test_has_two_tools_comparison(self):
        content = _read(UNDERWRITE)
        assert "Pipeline Underwriting" in content
        assert "BRRRR Calculator" in content

    def test_documents_pipeline_inputs(self):
        content = _read(UNDERWRITE)
        for field in [
            "purchase price",
            "rent",
            "tax",
            "insurance",
            "vacancy",
            "rehab",
            "maintenance",
            "management",
            "hoa",
        ]:
            assert field in content.lower(), f"Missing pipeline input: {field}"

    def test_documents_pipeline_metrics(self):
        content = _read(UNDERWRITE)
        for metric in ["GPR", "EGI", "NOI", "Cap Rate", "Cash-on-Cash", "MAO"]:
            assert metric in content, f"Missing metric: {metric}"

    def test_documents_brrrr_verdicts(self):
        content = _read(UNDERWRITE)
        for verdict in ["Full Cycle", "Partial Recycle", "Capital Trap"]:
            assert verdict in content, f"Missing verdict: {verdict}"

    def test_documents_dscr_warning(self):
        content = _read(UNDERWRITE)
        assert "DSCR" in content
        assert "1.25" in content

    def test_has_key_differences_table(self):
        content = _read(UNDERWRITE)
        assert "Key Differences" in content

    def test_links_to_brrrr_guide(self):
        content = _read(UNDERWRITE)
        assert "use-brrrr-calculator.md" in content

    def test_links_to_screen_properties(self):
        content = _read(UNDERWRITE)
        assert "screen-properties.md" in content


# ---------------------------------------------------------------------------
# ui-patterns.md
# ---------------------------------------------------------------------------

UI_PATTERNS = DOCS / "reference" / "ui-patterns.md"


class TestUIPatterns:
    def test_file_exists(self):
        assert UI_PATTERNS.exists(), f"{UI_PATTERNS} missing"

    def test_has_design_system_section(self):
        content = _read(UI_PATTERNS)
        assert "Design System" in content

    def test_mentions_tokens_css(self):
        content = _read(UI_PATTERNS)
        assert "tokens.css" in content

    def test_mentions_base_css(self):
        content = _read(UI_PATTERNS)
        assert "base.css" in content

    def test_has_page_layout(self):
        content = _read(UI_PATTERNS)
        assert "Page Layout" in content
        for cls in [".page-header", ".kpi-grid", ".card", ".data-table", ".filter-bar"]:
            assert cls in content, f"Missing class: {cls}"

    def test_has_data_table_patterns(self):
        content = _read(UI_PATTERNS)
        assert "Data Table Patterns" in content or "Table Patterns" in content
        assert ".chip-success" in content
        assert ".chip-warning" in content
        assert ".chip-danger" in content

    def test_has_form_patterns(self):
        content = _read(UI_PATTERNS)
        assert "Form Patterns" in content
        assert ".form-group" in content

    def test_has_navigation(self):
        content = _read(UI_PATTERNS)
        assert "Navigation" in content

    def test_has_loading_states(self):
        content = _read(UI_PATTERNS)
        assert "Loading States" in content

    def test_has_empty_states(self):
        content = _read(UI_PATTERNS)
        assert "Empty States" in content

    def test_has_accessibility(self):
        content = _read(UI_PATTERNS)
        assert "Accessibility" in content
        assert "role=" in content

    def test_mentions_no_bootstrap(self):
        content = _read(UI_PATTERNS)
        assert "Bootstrap" in content


# ---------------------------------------------------------------------------
# Cross-cutting planning docs
# ---------------------------------------------------------------------------

VISION = pathlib.Path(__file__).resolve().parent.parent / "VISION.md"
MILESTONES = pathlib.Path(__file__).resolve().parent.parent / "MILESTONES.md"
EXEC_QUEUE = pathlib.Path(__file__).resolve().parent.parent / "EXECUTION_QUEUE.md"
PLAN_TODAY = pathlib.Path(__file__).resolve().parent.parent / "plan-for-the-day.md"
DISCOVERY_DRAFT = DOCS / "product" / "discovery-draft.md"
PRODUCT_SPEC = DOCS / "product" / "spec.md"


class TestVision:
    def test_file_exists(self):
        assert VISION.exists()

    def test_has_north_star(self):
        content = _read(VISION)
        assert "North Star" in content

    def test_has_core_principles(self):
        content = _read(VISION)
        assert "Core Principles" in content

    def test_has_non_goals(self):
        content = _read(VISION)
        assert "Non-Goals" in content

    def test_has_riskiest_assumption(self):
        content = _read(VISION)
        assert "Riskiest Assumption" in content

    def test_has_how_this_connects(self):
        content = _read(VISION)
        assert "How This Connects" in content


class TestMilestones:
    def test_file_exists(self):
        assert MILESTONES.exists()

    def test_has_horizon_map(self):
        content = _read(MILESTONES)
        assert "Horizon Map" in content

    def test_has_release_gates(self):
        content = _read(MILESTONES)
        assert "Release Gates" in content

    def test_has_traceability(self):
        content = _read(MILESTONES)
        assert "Traceability" in content


class TestExecutionQueue:
    def test_file_exists(self):
        assert EXEC_QUEUE.exists()

    def test_has_priority_tiers(self):
        content = _read(EXEC_QUEUE)
        assert "P0" in content and "P1" in content

    def test_has_scope_drift_protection(self):
        content = _read(EXEC_QUEUE)
        assert "Scope Drift" in content or "scope drift" in content.lower()

    def test_has_bottom_up_feedback(self):
        content = _read(EXEC_QUEUE)
        assert "Bottom-Up" in content or "bottom-up" in content.lower()


class TestPlanForToday:
    def test_file_exists(self):
        assert PLAN_TODAY.exists()

    def test_has_primary_goal(self):
        content = _read(PLAN_TODAY)
        assert "Primary Goal" in content

    def test_has_tdd_protocol(self):
        content = _read(PLAN_TODAY)
        assert "TDD" in content or "Red" in content

    def test_has_retrospective(self):
        content = _read(PLAN_TODAY)
        assert "Retrospective" in content


class TestDiscoveryDraft:
    def test_file_exists(self):
        assert DISCOVERY_DRAFT.exists()

    def test_has_jtbd(self):
        content = _read(DISCOVERY_DRAFT)
        assert "JTBD" in content

    def test_has_riskiest_assumption(self):
        content = _read(DISCOVERY_DRAFT)
        assert "Riskiest Assumption" in content

    def test_has_acceptance_criterion(self):
        content = _read(DISCOVERY_DRAFT)
        assert "Acceptance Criterion" in content


class TestProductSpec:
    def test_file_exists(self):
        assert PRODUCT_SPEC.exists()

    def test_has_numbered_requirements(self):
        content = _read(PRODUCT_SPEC)
        assert "FR-1" in content

    def test_references_discovery_draft(self):
        content = _read(PRODUCT_SPEC)
        assert "discovery-draft" in content

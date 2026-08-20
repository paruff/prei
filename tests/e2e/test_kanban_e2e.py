"""Browser E2E for the Pipeline Kanban drag-and-drop advance."""

import pytest

from core.models import PipelineProperty

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture()
def kanban_property(db, e2e_login, growth_area) -> PipelineProperty:
    return PipelineProperty.objects.create(
        user=e2e_login,
        source_type=PipelineProperty.SourceType.HUD,
        source_id="KANBAN-0001",
        address="101 Boardwalk Blvd",
        city="Austin",
        state="TX",
        zip_code="78701",
        county="Travis",
        growth_area=growth_area,
        stage=PipelineProperty.Stage.SCREENING,
        status=PipelineProperty.Status.ACTIVE,
        screening_passed=True,
        price=90000,
        beds=3,
    )


class TestKanban:
    def test_board_renders_stage_columns(
        self, page, e2e_login, kanban_property
    ) -> None:
        page.goto("/pipeline/kanban/")
        assert page.locator(
            '#col-SCREENING .kanban-card[data-id="%d"]' % kanban_property.pk
        ).is_visible()
        assert page.locator(".kanban-column", has_text="Underwriting").is_visible()

    def test_drag_advances_stage(self, page, e2e_login, kanban_property) -> None:
        page.goto("/pipeline/kanban/")
        card_sel = '.kanban-card[data-id="%d"]' % kanban_property.pk
        assert page.locator(card_sel).is_visible()

        # Synthetic HTML5 Drag-and-Drop against the column's drop target.
        with page.expect_response(
            lambda r: r.url.endswith("/pipeline/kanban/") and r.request.method == "POST"
        ):
            page.evaluate(
                """({cardSel, targetSel}) => {
                    const card = document.querySelector(cardSel);
                    const target = document.querySelector(targetSel);
                    const dt = new DataTransfer();
                    card.dispatchEvent(new DragEvent('dragstart', {bubbles: true, dataTransfer: dt}));
                    target.dispatchEvent(new DragEvent('dragover', {bubbles: true, dataTransfer: dt}));
                    target.dispatchEvent(new DragEvent('drop', {bubbles: true, dataTransfer: dt}));
                    card.dispatchEvent(new DragEvent('dragend', {bubbles: true, dataTransfer: dt}));
                }""",
                arg={"cardSel": card_sel, "targetSel": "#col-UNDERWRITING"},
            )

        # Reload to prove the stage persisted, not just the DOM move.
        page.reload()
        assert page.locator(
            '#col-UNDERWRITING .kanban-card[data-id="%d"]' % kanban_property.pk
        ).is_visible()
        assert (
            page.locator(
                '#col-SCREENING .kanban-card[data-id="%d"]' % kanban_property.pk
            ).count()
            == 0
        )

        kanban_property.refresh_from_db()
        assert kanban_property.stage == PipelineProperty.Stage.UNDERWRITING

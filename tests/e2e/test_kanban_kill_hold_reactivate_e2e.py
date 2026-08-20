"""E2E tests for pipeline kanban kill/hold/reactivate endpoints."""

import pytest

from core.models import PipelineProperty

pytestmark = pytest.mark.django_db(transaction=True)

CSRF_JS = """
    const csrf = document.cookie.split('csrftoken=')[1]?.split(';')[0]
        || document.querySelector('[name=csrfmiddlewaretoken]')?.value
        || '';
"""


@pytest.fixture()
def killable_property(db, e2e_login, growth_area) -> PipelineProperty:
    return PipelineProperty.objects.create(
        user=e2e_login,
        source_type=PipelineProperty.SourceType.HUD,
        source_id="KILL-001",
        address="100 Kill St",
        city="Austin",
        state="TX",
        zip_code="78701",
        county="Travis",
        growth_area=growth_area,
        stage=PipelineProperty.Stage.UNDERWRITING,
        status=PipelineProperty.Status.ACTIVE,
        screening_passed=True,
        price=90000,
        beds=3,
    )


@pytest.fixture()
def held_property(db, e2e_login, growth_area) -> PipelineProperty:
    return PipelineProperty.objects.create(
        user=e2e_login,
        source_type=PipelineProperty.SourceType.HUD,
        source_id="HOLD-001",
        address="200 Hold St",
        city="Austin",
        state="TX",
        zip_code="78701",
        county="Travis",
        growth_area=growth_area,
        stage=PipelineProperty.Stage.OFFER,
        status=PipelineProperty.Status.ON_HOLD,
        screening_passed=True,
        price=95000,
        beds=3,
    )


@pytest.fixture()
def killed_property(db, e2e_login, growth_area) -> PipelineProperty:
    return PipelineProperty.objects.create(
        user=e2e_login,
        source_type=PipelineProperty.SourceType.HUD,
        source_id="KILLED-001",
        address="300 Killed St",
        city="Austin",
        state="TX",
        zip_code="78701",
        county="Travis",
        growth_area=growth_area,
        stage=PipelineProperty.Stage.DUE_DILIGENCE,
        status=PipelineProperty.Status.KILLED,
        screening_passed=True,
        price=100000,
        beds=3,
    )


class TestKanbanKillHoldReactivate:
    def test_kill_endpoint(self, page, e2e_login, killable_property) -> None:
        page.goto("/pipeline/kanban/")
        result = page.evaluate(
            "async (propertyId) => {"
            + CSRF_JS
            + """
                const fd = new FormData();
                fd.append('reason', 'Test kill');
                const r = await fetch(`/pipeline/${propertyId}/kill/`, {
                    method: "POST",
                    headers: {"X-CSRFToken": csrf},
                    body: fd,
                });
                return r.json();
            }""",
            killable_property.pk,
        )
        assert result["status"] == "ok"
        killable_property.refresh_from_db()
        assert killable_property.status == PipelineProperty.Status.KILLED
        assert killable_property.kill_reason == "Test kill"

    def test_hold_endpoint(self, page, e2e_login, killable_property) -> None:
        page.goto("/pipeline/kanban/")
        result = page.evaluate(
            "async (propertyId) => {"
            + CSRF_JS
            + """
                const fd = new FormData();
                fd.append('reason', 'Test hold');
                const r = await fetch(`/pipeline/${propertyId}/hold/`, {
                    method: "POST",
                    headers: {"X-CSRFToken": csrf},
                    body: fd,
                });
                return r.json();
            }""",
            killable_property.pk,
        )
        assert result["status"] == "ok"
        killable_property.refresh_from_db()
        assert killable_property.status == PipelineProperty.Status.ON_HOLD

    def test_reactivate_from_hold(self, page, e2e_login, held_property) -> None:
        page.goto("/pipeline/kanban/")
        result = page.evaluate(
            "async (propertyId) => {"
            + CSRF_JS
            + """
                const r = await fetch(`/pipeline/${propertyId}/reactivate/`, {
                    method: "POST",
                    headers: {"X-CSRFToken": csrf},
                });
                return r.json();
            }""",
            held_property.pk,
        )
        assert result["status"] == "ok"
        held_property.refresh_from_db()
        assert held_property.status == PipelineProperty.Status.ACTIVE
        assert held_property.stage == PipelineProperty.Stage.OFFER

    def test_reactivate_from_killed(self, page, e2e_login, killed_property) -> None:
        page.goto("/pipeline/kanban/")
        result = page.evaluate(
            "async (propertyId) => {"
            + CSRF_JS
            + """
                const r = await fetch(`/pipeline/${propertyId}/reactivate/`, {
                    method: "POST",
                    headers: {"X-CSRFToken": csrf},
                });
                return r.json();
            }""",
            killed_property.pk,
        )
        assert result["status"] == "ok"
        killed_property.refresh_from_db()
        assert killed_property.status == PipelineProperty.Status.ACTIVE

    def test_kill_405_on_get(self, page, e2e_login, killable_property) -> None:
        response = page.request.get(f"/pipeline/{killable_property.pk}/kill/")
        assert response.status == 405

    def test_hold_405_on_get(self, page, e2e_login, killable_property) -> None:
        response = page.request.get(f"/pipeline/{killable_property.pk}/hold/")
        assert response.status == 405

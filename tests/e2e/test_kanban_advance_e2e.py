"""E2E tests for pipeline kanban advance endpoint."""

import pytest

from core.models import PipelineProperty

pytestmark = pytest.mark.django_db(transaction=True)

CSRF_JS = """
    const csrf = document.cookie.split('csrftoken=')[1]?.split(';')[0]
        || document.querySelector('[name=csrfmiddlewaretoken]')?.value
        || '';
"""


@pytest.fixture()
def advance_test_property(db, e2e_login, growth_area) -> PipelineProperty:
    return PipelineProperty.objects.create(
        user=e2e_login,
        source_type=PipelineProperty.SourceType.HUD,
        source_id="ADV-TEST-001",
        address="200 Advance Ave",
        city="Austin",
        state="TX",
        zip_code="78701",
        county="Travis",
        growth_area=growth_area,
        stage=PipelineProperty.Stage.SCREENING,
        status=PipelineProperty.Status.ACTIVE,
        screening_passed=True,
        price=95000,
        beds=3,
    )


class TestKanbanAdvanceEndpoint:
    def test_advance_via_fetch(self, page, e2e_login, advance_test_property) -> None:
        """Advance moves property to next sequential stage."""
        page.goto("/pipeline/kanban/")
        result = page.evaluate(
            "async (propertyId) => {"
            + CSRF_JS
            + """
                const r = await fetch(`/pipeline/${propertyId}/advance/`, {
                    method: "POST",
                    headers: {"X-CSRFToken": csrf},
                });
                return r.json();
            }""",
            advance_test_property.pk,
        )
        assert result["status"] == "ok"
        assert result["stage"] == "UNDERWRITING"

        advance_test_property.refresh_from_db()
        assert advance_test_property.stage == PipelineProperty.Stage.UNDERWRITING

    def test_advance_405_on_get(self, page, e2e_login, advance_test_property) -> None:
        """GET to advance endpoint returns 405 Method Not Allowed."""
        response = page.request.get(f"/pipeline/{advance_test_property.pk}/advance/")
        assert response.status == 405

    def test_advance_forbidden_other_user(self, page, e2e_login, growth_area) -> None:
        """Other user's property returns 404."""
        from django.contrib.auth import get_user_model

        User = get_user_model()
        other = User.objects.create_user("other_user", "o@o.com", "pass123")
        prop = PipelineProperty.objects.create(
            user=other,
            source_type=PipelineProperty.SourceType.HUD,
            source_id="OTHER-ADV-001",
            address="300 Other St",
            city="Austin",
            state="TX",
            zip_code="78701",
            county="Travis",
            growth_area=growth_area,
            stage=PipelineProperty.Stage.SCREENING,
            status=PipelineProperty.Status.ACTIVE,
            screening_passed=True,
            price=90000,
            beds=2,
        )
        page.goto("/pipeline/kanban/")
        result = page.evaluate(
            "async (propertyId) => {"
            + CSRF_JS
            + """
                const r = await fetch(`/pipeline/${propertyId}/advance/`, {
                    method: "POST",
                    headers: {"X-CSRFToken": csrf},
                });
                return {status: r.status, body: await r.text()};
            }""",
            prop.pk,
        )
        assert result["status"] == 404

    def test_advance_boundary_stabilized(
        self, page, e2e_login, advance_test_property
    ) -> None:
        """Cannot advance past STABILIZED — returns 400 with error."""
        advance_test_property.stage = PipelineProperty.Stage.STABILIZED
        advance_test_property.save(update_fields=["stage"])
        page.goto("/pipeline/kanban/")
        result = page.evaluate(
            "async (propertyId) => {"
            + CSRF_JS
            + """
                const r = await fetch(`/pipeline/${propertyId}/advance/`, {
                    method: "POST",
                    headers: {"X-CSRFToken": csrf},
                });
                return {status: r.status, body: await r.json()};
            }""",
            advance_test_property.pk,
        )
        assert result["status"] == 400
        assert "error" in result["body"]

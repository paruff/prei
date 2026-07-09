"""Acceptance tests for the Pipeline review queue (PIPE-UX-1)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from core.models import PipelineProperty


def _create_pipeline_property(
    user,
    *,
    address: str = "123 Test St",
    stage: str = PipelineProperty.Stage.SCREENING,
    status: str = PipelineProperty.Status.ACTIVE,
    screening_passed: bool = True,
    price: Decimal | None = Decimal("200000"),
    estimated_rent: Decimal | None = Decimal("1500"),
    gacs_score: Decimal | None = Decimal("75.00"),
    source_type: str = PipelineProperty.SourceType.VRM,
) -> PipelineProperty:
    """Helper to create a PipelineProperty with defaults."""
    return PipelineProperty.objects.create(
        user=user,
        source_type=source_type,
        source_id=f"test-{address}",
        address=address,
        stage=stage,
        status=status,
        screening_passed=screening_passed,
        price=price,
        estimated_rent=estimated_rent,
        gacs_score=gacs_score,
        discovered_at=timezone.now(),
        created_at=timezone.now(),
    )


# ═══════════════════════════════════════════════════════════════════════
# Acceptance tests
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.django_db
class TestReviewQueueView:
    """Tests for GET /pipeline/review/."""

    def test_returns_200_when_no_properties(self, client, user) -> None:
        """GET /pipeline/review/ returns 200 even when user has no properties."""
        client.force_login(user)
        response = client.get(reverse("pipeline_review_queue"))
        assert response.status_code == 200

    def test_shows_empty_state_when_no_passed_properties(self, client, user) -> None:
        """Empty-state shown when no SCREENING+screening_passed=True properties."""
        client.force_login(user)
        response = client.get(reverse("pipeline_review_queue"))
        assert response.status_code == 200
        assert b"empty-state" in response.content

    def test_shows_cards_for_passed_screening_only(self, client, user) -> None:
        """Only SCREENING+screening_passed=True properties are shown."""
        # Passed screening
        _create_pipeline_property(user, address="101 Passed Ln")
        _create_pipeline_property(user, address="102 Passed Ln")

        # Not passed
        _create_pipeline_property(
            user, address="201 Marginal St", screening_passed=False
        )

        # Different stage
        _create_pipeline_property(
            user,
            address="301 Discovered Ave",
            stage=PipelineProperty.Stage.DISCOVERED,
        )

        client.force_login(user)
        response = client.get(reverse("pipeline_review_queue"))

        assert response.status_code == 200
        html = response.content.decode()

        # Should show passed properties
        assert "101 Passed Ln" in html
        assert "102 Passed Ln" in html

        # Should NOT show non-passed or non-SCREENING properties
        assert "201 Marginal St" not in html
        assert "301 Discovered Ave" not in html

    def test_each_card_has_three_action_buttons(self, client, user) -> None:
        """Each card has Underwrite, Hold, and Kill buttons."""
        _create_pipeline_property(user, address="101 Action Ln")

        client.force_login(user)
        response = client.get(reverse("pipeline_review_queue"))
        html = response.content.decode()

        # Underwrite link
        assert "Underwrite" in html
        # Hold form button
        assert "Hold" in html

    def test_pagination_shown_when_more_than_20(self, client, user) -> None:
        """Pagination controls appear when > 20 results."""
        for i in range(25):
            _create_pipeline_property(
                user, address=f"{i:03d} Pagination St", gacs_score=Decimal("50.00")
            )

        client.force_login(user)
        response = client.get(reverse("pipeline_review_queue"))
        html = response.content.decode()

        assert "Page 1 of 2" in html
        assert "Next" in html

    def test_gacs_score_ordering(self, client, user) -> None:
        """Properties ordered by gacs_score descending."""
        _create_pipeline_property(
            user, address="101 Low Score", gacs_score=Decimal("30.00")
        )
        _create_pipeline_property(
            user, address="102 High Score", gacs_score=Decimal("90.00")
        )
        _create_pipeline_property(
            user, address="103 Medium Score", gacs_score=Decimal("60.00")
        )

        client.force_login(user)
        response = client.get(reverse("pipeline_review_queue"))
        html = response.content.decode()

        # High score should appear before low score
        hi_pos = html.index("102 High Score")
        med_pos = html.index("103 Medium Score")
        lo_pos = html.index("101 Low Score")

        assert hi_pos < med_pos < lo_pos, (
            "Properties should be sorted by gacs_score descending"
        )


@pytest.mark.django_db
class TestAdvanceStageView:
    """Tests for POST /pipeline/<pk>/advance/."""

    def test_hold_sets_status_on_hold(self, client, user) -> None:
        """POST with action=hold sets status to ON_HOLD."""
        prop = _create_pipeline_property(user)
        assert prop.status == PipelineProperty.Status.ACTIVE

        client.force_login(user)
        client.post(
            reverse("pipeline_advance_stage", args=[prop.pk]),
            {"action": "hold"},
        )

        prop.refresh_from_db()
        assert prop.status == PipelineProperty.Status.ON_HOLD

    def test_hold_redirects_to_review_queue(self, client, user) -> None:
        """Hold action redirects back to review queue."""
        prop = _create_pipeline_property(user)

        client.force_login(user)
        response = client.post(
            reverse("pipeline_advance_stage", args=[prop.pk]),
            {"action": "hold"},
        )

        assert response.status_code == 302
        assert response.url == reverse("pipeline_review_queue")

    def test_get_returns_405(self, client, user) -> None:
        """GET request returns 405 Method Not Allowed."""
        prop = _create_pipeline_property(user)

        client.force_login(user)
        response = client.get(
            reverse("pipeline_advance_stage", args=[prop.pk]),
        )

        assert response.status_code == 405

    def test_unknown_action_returns_warning(self, client, user) -> None:
        """Unknown action returns warning message."""
        prop = _create_pipeline_property(user)

        client.force_login(user)
        response = client.post(
            reverse("pipeline_advance_stage", args=[prop.pk]),
            {"action": "unknown_action"},
            follow=True,
        )

        assert response.status_code == 200
        assert b"Unknown action" in response.content

    def test_404_for_wrong_user(self, client, user, second_user) -> None:
        """Other user's property returns 404."""
        prop = _create_pipeline_property(second_user)

        client.force_login(user)
        response = client.post(
            reverse("pipeline_advance_stage", args=[prop.pk]),
            {"action": "hold"},
        )

        assert response.status_code == 404


@pytest.mark.django_db
class TestReviewQueueNav:
    """Tests for nav integration."""

    def test_review_queue_link_in_nav(self, client, user) -> None:
        """The Review queue nav link appears in the page."""
        client.force_login(user)
        response = client.get(reverse("pipeline_review_queue"))

        # The nav should include a link to the review queue
        assert reverse("pipeline_review_queue") in response.content.decode()

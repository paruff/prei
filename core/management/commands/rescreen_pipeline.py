"""Re-screen every pipeline property so stored verdicts match current rules."""

from django.core.management.base import BaseCommand

from core.models import PipelineProperty, ScreeningCriteria
from core.services.pipeline import get_source_record
from core.services.screening import screen_property


class Command(BaseCommand):
    help = "Re-screen all pipeline properties against their owner's criteria."

    def handle(self, *args, **options):
        count = 0
        for criteria in ScreeningCriteria.objects.select_related("user"):
            for pp in PipelineProperty.objects.filter(user=criteria.user):
                result = screen_property(
                    pp, criteria, source_record=get_source_record(pp)
                )
                if pp.screening_passed != result.passed:
                    pp.screening_passed = result.passed
                    pp.save(update_fields=["screening_passed", "updated_at"])
                count += 1
        self.stdout.write(f"Re-screened {count} pipeline properties")

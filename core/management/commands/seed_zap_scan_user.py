import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        "Idempotently seed a low-privilege user for authenticated OWASP ZAP "
        "scans. Reads credentials from ZAP_AUTH_USERNAME/ZAP_AUTH_PASSWORD "
        "env vars. Intended for ephemeral CI databases only."
    )

    def handle(self, *args, **options):
        username = os.environ.get("ZAP_AUTH_USERNAME")
        password = os.environ.get("ZAP_AUTH_PASSWORD")
        if not username or not password:
            raise CommandError(
                "ZAP_AUTH_USERNAME and ZAP_AUTH_PASSWORD env vars are required"
            )

        User = get_user_model()
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "is_staff": False,
                "is_superuser": False,
                "is_active": True,
            },
        )
        user.is_staff = False
        user.is_superuser = False
        user.is_active = True
        user.set_password(password)
        user.save()

        action = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{action} ZAP scan user '{username}'"))

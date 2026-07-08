import logging
import sys

import django

from django.apps import AppConfig

logger = logging.getLogger("prei.config")


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self) -> None:
        """Log application version on startup.

        Uses structured extra fields so log aggregators (ELK, Grafana, etc.)
        can index them as queryable fields rather than parsing a formatted
        string.
        """
        from .context_processors import _read_git_commit, _read_version

        version = _read_version()
        commit = _read_git_commit()

        logger.info(
            "prei started",
            extra={
                "version": version,
                "git_commit": commit,
                "python_version": sys.version.split()[0],
                "django_version": django.get_version(),
            },
        )

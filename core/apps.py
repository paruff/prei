import logging

from django.apps import AppConfig

logger = logging.getLogger("prei.config")


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self) -> None:
        """Log application version on startup."""
        from .context_processors import _read_git_commit, _read_version

        version = _read_version()
        commit = _read_git_commit()
        logger.info("prei version=%s commit=%s", version, commit)

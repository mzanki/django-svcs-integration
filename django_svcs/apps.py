from __future__ import annotations

import atexit

from django.apps import AppConfig

import svcs


class DjangoSvcsConfig(AppConfig):
    """
    AppConfig for *django-svcs*.

    Creates a process-wide :class:`svcs.Registry` and attaches it to the
    AppConfig instance on :meth:`ready`. Registers an ``atexit`` hook so
    pending registry-close callbacks fire on graceful interpreter shutdown.

    For ASGI deployments, prefer calling :func:`django_svcs.aclose_registry`
    from your ASGI lifespan handler so async ``on_registry_close`` callbacks
    can run.
    """

    name = "django_svcs"
    verbose_name = "Django svcs"

    registry: svcs.Registry

    def ready(self) -> None:
        if not hasattr(self, "registry"):
            self.registry = svcs.Registry()
            atexit.register(self.registry.close)

from __future__ import annotations

from ._container import (
    aget,
    aget_abstract,
    get,
    get_abstract,
    get_pings,
    svcs_from,
)
from ._registry import (
    aclose_registry,
    bind_local_factory,
    bind_local_value,
    close_registry,
    factory,
    get_registry,
    overwrite_factory,
    overwrite_value,
    register_factory,
    register_value,
)
from .middleware import SvcsMiddleware
from .views import AsyncHealthCheckView, HealthCheckView


default_app_config = "django_svcs.apps.DjangoSvcsConfig"


__all__ = [
    "AsyncHealthCheckView",
    "HealthCheckView",
    "SvcsMiddleware",
    "aclose_registry",
    "aget",
    "aget_abstract",
    "bind_local_factory",
    "bind_local_value",
    "close_registry",
    "default_app_config",
    "factory",
    "get",
    "get_abstract",
    "get_pings",
    "get_registry",
    "overwrite_factory",
    "overwrite_value",
    "register_factory",
    "register_value",
    "svcs_from",
]

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, cast

from django.apps import apps

import svcs


if TYPE_CHECKING:
    from django.http import HttpRequest

    from typing_extensions import TypeForm

    from .apps import DjangoSvcsConfig


def factory(fn: Callable[[svcs.Container], Any]) -> Callable[[svcs.Container], Any]:
    """
    Wrap *fn* so svcs's container-introspection always passes the container.

    ``svcs.Registry.register_factory`` decides whether to pass the
    container based on the factory's *first parameter name* (must be
    ``svcs_container``) or *first parameter annotation* (must be
    ``svcs.Container``). Lambdas can't carry annotations and short
    parameter names like ``c`` fail the check — svcs then calls the
    factory with zero arguments and you see a confusing ``TypeError``.

    Use this adapter when registering a lambda or any callable whose
    signature doesn't match svcs's introspection rules:

    .. code-block:: python

        django_svcs.register_factory(
            SubscribeHandler,
            django_svcs.factory(lambda c: SubscribeHandler(service=c.get(Svc))),
        )

    The wrapper is itself an annotated function, so svcs sees a
    container-taking factory and the inner lambda receives the container
    unchanged.
    """

    def _adapted(svcs_container: svcs.Container) -> Any:
        return fn(svcs_container)

    return _adapted


def get_registry() -> svcs.Registry:
    """
    Return the process-wide :class:`svcs.Registry` attached to the
    ``django_svcs`` AppConfig.
    """
    return cast("DjangoSvcsConfig", apps.get_app_config("django_svcs")).registry


def register_factory(
    svc_type: TypeForm[Any],
    factory: Callable,
    *,
    enter: bool = True,
    ping: Callable | None = None,
    on_registry_close: Callable | Awaitable | None = None,
    suppress_context_exit: bool = True,
) -> None:
    """
    Register *factory* for *svc_type* on the process-wide registry.

    See Also:
        :meth:`svcs.Registry.register_factory`
    """
    get_registry().register_factory(
        svc_type,
        factory,
        enter=enter,
        ping=ping,
        on_registry_close=on_registry_close,
        suppress_context_exit=suppress_context_exit,
    )


def register_value(
    svc_type: TypeForm[Any],
    value: object,
    *,
    enter: bool = False,
    ping: Callable | None = None,
    on_registry_close: Callable | Awaitable | None = None,
    suppress_context_exit: bool = True,
) -> None:
    """
    Register *value* for *svc_type* on the process-wide registry.

    See Also:
        :meth:`svcs.Registry.register_value`
    """
    get_registry().register_value(
        svc_type,
        value,
        enter=enter,
        ping=ping,
        on_registry_close=on_registry_close,
        suppress_context_exit=suppress_context_exit,
    )


def overwrite_factory(
    request: HttpRequest,
    svc_type: TypeForm[Any],
    factory: Callable,
    *,
    enter: bool = True,
    ping: Callable | None = None,
    on_registry_close: Callable | Awaitable | None = None,
    suppress_context_exit: bool = True,
) -> None:
    """
    Overwrite *svc_type*'s factory on the process registry and reset the
    container attached to *request* so the next ``svcs_from(request).get()``
    rebuilds the service.

    See Also:
        - :meth:`svcs.Registry.register_factory`
        - :meth:`svcs.Container.close`
    """
    from ._container import svcs_from

    container = svcs_from(request)
    container.registry.register_factory(
        svc_type,
        factory,
        enter=enter,
        ping=ping,
        on_registry_close=on_registry_close,
        suppress_context_exit=suppress_context_exit,
    )
    container.close()
    _reset_container(request)


def overwrite_value(
    request: HttpRequest,
    svc_type: TypeForm[Any],
    value: object,
    *,
    enter: bool = False,
    ping: Callable | None = None,
    on_registry_close: Callable | Awaitable | None = None,
    suppress_context_exit: bool = True,
) -> None:
    """
    Overwrite *svc_type*'s value on the process registry and reset the
    container attached to *request*.

    See Also:
        - :meth:`svcs.Registry.register_value`
        - :meth:`svcs.Container.close`
    """
    from ._container import svcs_from

    container = svcs_from(request)
    container.registry.register_value(
        svc_type,
        value,
        enter=enter,
        ping=ping,
        on_registry_close=on_registry_close,
        suppress_context_exit=suppress_context_exit,
    )
    container.close()
    _reset_container(request)


def bind_local_value(
    request: HttpRequest,
    svc_type: TypeForm[Any],
    value: object,
    *,
    enter: bool = False,
    ping: Callable | None = None,
    on_registry_close: Callable | Awaitable | None = None,
) -> None:
    """
    Bind *value* for *svc_type* on the **per-request** container.

    Unlike :func:`overwrite_value`, this does **not** mutate the process-wide
    registry — the binding lives only for the lifetime of the current
    request's container. Use this from middleware to publish request-scoped
    services (current user, request id, tenant context) without leaking
    state into subsequent requests.

    See Also:
        - :meth:`svcs.Container.register_local_value`
        - :func:`overwrite_value` (for test-only process-wide overrides)
    """
    from ._container import svcs_from

    svcs_from(request).register_local_value(
        svc_type,
        value,
        enter=enter,
        ping=ping,
        on_registry_close=on_registry_close,
    )


def bind_local_factory(
    request: HttpRequest,
    svc_type: TypeForm[Any],
    factory: Callable,
    *,
    enter: bool = True,
    ping: Callable | None = None,
    on_registry_close: Callable | Awaitable | None = None,
) -> None:
    """
    Bind *factory* for *svc_type* on the **per-request** container.

    Factory variant of :func:`bind_local_value` — use when each
    ``container.get(svc_type)`` should build a fresh instance scoped to
    this request.

    See Also:
        - :meth:`svcs.Container.register_local_factory`
        - :func:`overwrite_factory` (for test-only process-wide overrides)
    """
    from ._container import svcs_from

    svcs_from(request).register_local_factory(
        svc_type,
        factory,
        enter=enter,
        ping=ping,
        on_registry_close=on_registry_close,
    )


def close_registry() -> None:
    """
    Synchronously close the process-wide registry, running its
    ``on_registry_close`` callbacks. Safe to call multiple times.

    See Also:
        :meth:`svcs.Registry.close`
    """
    get_registry().close()


async def aclose_registry() -> None:
    """
    Async-close the process-wide registry. Use this from an ASGI lifespan
    shutdown handler so async ``on_registry_close`` callbacks can run.

    See Also:
        :meth:`svcs.Registry.aclose`
    """
    await get_registry().aclose()


def _reset_container(request: HttpRequest) -> None:
    if hasattr(request, "svcs_container"):
        delattr(request, "svcs_container")

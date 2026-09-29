from __future__ import annotations

from typing import TYPE_CHECKING, Any, overload

import svcs
from svcs._core import T1, T2, T3, T4, T5, T6, T7, T8, T9, T10

from ._registry import get_registry


if TYPE_CHECKING:
    from django.http import HttpRequest

    from typing_extensions import TypeForm


_REQUEST_ATTR = "svcs_container"


def svcs_from(request: HttpRequest) -> svcs.Container:
    """
    Return the :class:`svcs.Container` attached to *request*, creating one
    lazily if absent.

    The container lives for the duration of the request; cleanup is the
    responsibility of :class:`django_svcs.SvcsMiddleware`. If the middleware
    is not installed, callers must close the container themselves.
    """
    container = getattr(request, _REQUEST_ATTR, None)
    if container is None:
        container = svcs.Container(get_registry())
        setattr(request, _REQUEST_ATTR, container)
    return container


@overload
def get(request: HttpRequest, svc_type: TypeForm[T1], /) -> T1: ...


@overload
def get(request: HttpRequest, svc_type1: TypeForm[T1], svc_type2: TypeForm[T2], /) -> tuple[T1, T2]: ...


@overload
def get(
    request: HttpRequest, svc_type1: TypeForm[T1], svc_type2: TypeForm[T2], svc_type3: TypeForm[T3], /
) -> tuple[T1, T2, T3]: ...


@overload
def get(
    request: HttpRequest,
    svc_type1: TypeForm[T1],
    svc_type2: TypeForm[T2],
    svc_type3: TypeForm[T3],
    svc_type4: TypeForm[T4],
    /,
) -> tuple[T1, T2, T3, T4]: ...


@overload
def get(
    request: HttpRequest,
    svc_type1: TypeForm[T1],
    svc_type2: TypeForm[T2],
    svc_type3: TypeForm[T3],
    svc_type4: TypeForm[T4],
    svc_type5: TypeForm[T5],
    /,
) -> tuple[T1, T2, T3, T4, T5]: ...


@overload
def get(
    request: HttpRequest,
    svc_type1: TypeForm[T1],
    svc_type2: TypeForm[T2],
    svc_type3: TypeForm[T3],
    svc_type4: TypeForm[T4],
    svc_type5: TypeForm[T5],
    svc_type6: TypeForm[T6],
    /,
) -> tuple[T1, T2, T3, T4, T5, T6]: ...


@overload
def get(
    request: HttpRequest,
    svc_type1: TypeForm[T1],
    svc_type2: TypeForm[T2],
    svc_type3: TypeForm[T3],
    svc_type4: TypeForm[T4],
    svc_type5: TypeForm[T5],
    svc_type6: TypeForm[T6],
    svc_type7: TypeForm[T7],
    /,
) -> tuple[T1, T2, T3, T4, T5, T6, T7]: ...


@overload
def get(
    request: HttpRequest,
    svc_type1: TypeForm[T1],
    svc_type2: TypeForm[T2],
    svc_type3: TypeForm[T3],
    svc_type4: TypeForm[T4],
    svc_type5: TypeForm[T5],
    svc_type6: TypeForm[T6],
    svc_type7: TypeForm[T7],
    svc_type8: TypeForm[T8],
    /,
) -> tuple[T1, T2, T3, T4, T5, T6, T7, T8]: ...


@overload
def get(
    request: HttpRequest,
    svc_type1: TypeForm[T1],
    svc_type2: TypeForm[T2],
    svc_type3: TypeForm[T3],
    svc_type4: TypeForm[T4],
    svc_type5: TypeForm[T5],
    svc_type6: TypeForm[T6],
    svc_type7: TypeForm[T7],
    svc_type8: TypeForm[T8],
    svc_type9: TypeForm[T9],
    /,
) -> tuple[T1, T2, T3, T4, T5, T6, T7, T8, T9]: ...


@overload
def get(
    request: HttpRequest,
    svc_type1: TypeForm[T1],
    svc_type2: TypeForm[T2],
    svc_type3: TypeForm[T3],
    svc_type4: TypeForm[T4],
    svc_type5: TypeForm[T5],
    svc_type6: TypeForm[T6],
    svc_type7: TypeForm[T7],
    svc_type8: TypeForm[T8],
    svc_type9: TypeForm[T9],
    svc_type10: TypeForm[T10],
    /,
) -> tuple[T1, T2, T3, T4, T5, T6, T7, T8, T9, T10]: ...


def get(request: HttpRequest, *svc_types: TypeForm[Any]) -> object:
    """
    Resolve one or more services from the container attached to *request*.

    See Also:
        :meth:`svcs.Container.get`
    """
    return svcs_from(request).get(*svc_types)


def get_abstract(request: HttpRequest, *svc_types: TypeForm[Any]) -> Any:
    """
    Resolve abstract service types from the container attached to *request*.

    Deprecated: use :func:`get`, which now accepts abstract types directly.
    Kept for compatibility without emitting a warning.

    See Also:
        :meth:`svcs.Container.get_abstract`
    """
    return svcs_from(request).get_abstract(*svc_types)


@overload
async def aget(request: HttpRequest, svc_type: TypeForm[T1], /) -> T1: ...


@overload
async def aget(request: HttpRequest, svc_type1: TypeForm[T1], svc_type2: TypeForm[T2], /) -> tuple[T1, T2]: ...


@overload
async def aget(
    request: HttpRequest, svc_type1: TypeForm[T1], svc_type2: TypeForm[T2], svc_type3: TypeForm[T3], /
) -> tuple[T1, T2, T3]: ...


@overload
async def aget(
    request: HttpRequest,
    svc_type1: TypeForm[T1],
    svc_type2: TypeForm[T2],
    svc_type3: TypeForm[T3],
    svc_type4: TypeForm[T4],
    /,
) -> tuple[T1, T2, T3, T4]: ...


@overload
async def aget(
    request: HttpRequest,
    svc_type1: TypeForm[T1],
    svc_type2: TypeForm[T2],
    svc_type3: TypeForm[T3],
    svc_type4: TypeForm[T4],
    svc_type5: TypeForm[T5],
    /,
) -> tuple[T1, T2, T3, T4, T5]: ...


@overload
async def aget(
    request: HttpRequest,
    svc_type1: TypeForm[T1],
    svc_type2: TypeForm[T2],
    svc_type3: TypeForm[T3],
    svc_type4: TypeForm[T4],
    svc_type5: TypeForm[T5],
    svc_type6: TypeForm[T6],
    /,
) -> tuple[T1, T2, T3, T4, T5, T6]: ...


@overload
async def aget(
    request: HttpRequest,
    svc_type1: TypeForm[T1],
    svc_type2: TypeForm[T2],
    svc_type3: TypeForm[T3],
    svc_type4: TypeForm[T4],
    svc_type5: TypeForm[T5],
    svc_type6: TypeForm[T6],
    svc_type7: TypeForm[T7],
    /,
) -> tuple[T1, T2, T3, T4, T5, T6, T7]: ...


@overload
async def aget(
    request: HttpRequest,
    svc_type1: TypeForm[T1],
    svc_type2: TypeForm[T2],
    svc_type3: TypeForm[T3],
    svc_type4: TypeForm[T4],
    svc_type5: TypeForm[T5],
    svc_type6: TypeForm[T6],
    svc_type7: TypeForm[T7],
    svc_type8: TypeForm[T8],
    /,
) -> tuple[T1, T2, T3, T4, T5, T6, T7, T8]: ...


@overload
async def aget(
    request: HttpRequest,
    svc_type1: TypeForm[T1],
    svc_type2: TypeForm[T2],
    svc_type3: TypeForm[T3],
    svc_type4: TypeForm[T4],
    svc_type5: TypeForm[T5],
    svc_type6: TypeForm[T6],
    svc_type7: TypeForm[T7],
    svc_type8: TypeForm[T8],
    svc_type9: TypeForm[T9],
    /,
) -> tuple[T1, T2, T3, T4, T5, T6, T7, T8, T9]: ...


@overload
async def aget(
    request: HttpRequest,
    svc_type1: TypeForm[T1],
    svc_type2: TypeForm[T2],
    svc_type3: TypeForm[T3],
    svc_type4: TypeForm[T4],
    svc_type5: TypeForm[T5],
    svc_type6: TypeForm[T6],
    svc_type7: TypeForm[T7],
    svc_type8: TypeForm[T8],
    svc_type9: TypeForm[T9],
    svc_type10: TypeForm[T10],
    /,
) -> tuple[T1, T2, T3, T4, T5, T6, T7, T8, T9, T10]: ...


async def aget(request: HttpRequest, *svc_types: TypeForm[Any]) -> object:
    """
    Async-resolve one or more services from the container attached to *request*.

    See Also:
        :meth:`svcs.Container.aget`
    """
    return await svcs_from(request).aget(*svc_types)


async def aget_abstract(request: HttpRequest, *svc_types: TypeForm[Any]) -> Any:
    """
    Async-resolve abstract service types from the container attached to *request*.

    Deprecated: use :func:`aget`, which now accepts abstract types directly.
    Kept for compatibility without emitting a warning.

    See Also:
        :meth:`svcs.Container.aget_abstract`
    """
    return await svcs_from(request).aget_abstract(*svc_types)


def get_pings(request: HttpRequest) -> list[svcs.ServicePing]:
    """
    Return all :class:`svcs.ServicePing` instances for services registered
    with a ping callable.

    See Also:
        :meth:`svcs.Container.get_pings`
    """
    return svcs_from(request).get_pings()

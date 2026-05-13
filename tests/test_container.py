"""
Tests for ``django_svcs._container``: ``svcs_from``, ``get`` / ``aget``,
``get_abstract``, ``get_pings``, ``overwrite_factory`` / ``overwrite_value``.

These exercise the request-bound container API independently of the
middleware. Each test fabricates a request via :class:`RequestFactory` /
:class:`AsyncRequestFactory` and closes the container manually.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from django.test import AsyncRequestFactory, RequestFactory, TestCase

import svcs

import django_svcs


@runtime_checkable
class _Greeter(Protocol):
    def hello(self) -> str: ...


class _SyncGreeter:
    def hello(self) -> str:
        return "sync"


class _OtherGreeter:
    def hello(self) -> str:
        return "other"


def _drop(*types: type) -> None:
    reg = django_svcs.get_registry()
    for t in types:
        reg._services.pop(t, None)


class SvcsFromTests(TestCase):
    def test_lazy_creation_without_middleware(self):
        request = RequestFactory().get("/")

        container = django_svcs.svcs_from(request)

        self.assertIsInstance(container, svcs.Container)
        self.assertIs(django_svcs.svcs_from(request), container)

    def test_attaches_attribute_named_svcs_container(self):
        request = RequestFactory().get("/")
        container = django_svcs.svcs_from(request)

        self.assertIs(request.svcs_container, container)


class GetTests(TestCase):
    def setUp(self):
        django_svcs.register_factory(_SyncGreeter, _SyncGreeter)
        django_svcs.register_factory(_OtherGreeter, _OtherGreeter)

    def tearDown(self):
        _drop(_SyncGreeter, _OtherGreeter)

    def test_get_single_returns_instance(self):
        request = RequestFactory().get("/")
        try:
            svc = django_svcs.get(request, _SyncGreeter)
            self.assertIsInstance(svc, _SyncGreeter)
            self.assertEqual(svc.hello(), "sync")
        finally:
            django_svcs.svcs_from(request).close()

    def test_get_two_returns_tuple(self):
        request = RequestFactory().get("/")
        try:
            a, b = django_svcs.get(request, _SyncGreeter, _OtherGreeter)
            self.assertEqual(a.hello(), "sync")
            self.assertEqual(b.hello(), "other")
        finally:
            django_svcs.svcs_from(request).close()

    def test_get_caches_within_request(self):
        request = RequestFactory().get("/")
        try:
            self.assertIs(
                django_svcs.get(request, _SyncGreeter),
                django_svcs.get(request, _SyncGreeter),
            )
        finally:
            django_svcs.svcs_from(request).close()


class GetAbstractTests(TestCase):
    def tearDown(self):
        _drop(_Greeter)

    def test_get_abstract_resolves_protocol_type(self):
        django_svcs.register_factory(_Greeter, _SyncGreeter)
        request = RequestFactory().get("/")

        try:
            svc = django_svcs.get_abstract(request, _Greeter)
            self.assertEqual(svc.hello(), "sync")
        finally:
            django_svcs.svcs_from(request).close()


class AgetTests(TestCase):
    def setUp(self):
        async def factory():
            yield _SyncGreeter()

        django_svcs.register_factory(_SyncGreeter, factory)

    def tearDown(self):
        _drop(_SyncGreeter)

    async def test_aget_returns_instance(self):
        request = AsyncRequestFactory().get("/")
        try:
            svc = await django_svcs.aget(request, _SyncGreeter)
            self.assertEqual(svc.hello(), "sync")
        finally:
            await django_svcs.svcs_from(request).aclose()


class GetPingsTests(TestCase):
    def tearDown(self):
        _drop(_SyncGreeter)

    def test_get_pings_returns_registered_pings(self):
        django_svcs.register_factory(_SyncGreeter, _SyncGreeter, ping=lambda _svc: None)
        request = RequestFactory().get("/")

        try:
            pings = django_svcs.get_pings(request)
            names = [p.name for p in pings]
            self.assertIn("tests.test_container._SyncGreeter", names)
        finally:
            django_svcs.svcs_from(request).close()

    def test_get_pings_empty_when_no_pings_registered(self):
        django_svcs.register_factory(_SyncGreeter, _SyncGreeter)
        request = RequestFactory().get("/")

        try:
            self.assertEqual(django_svcs.get_pings(request), [])
        finally:
            django_svcs.svcs_from(request).close()


class OverwriteFactoryTests(TestCase):
    def setUp(self):
        django_svcs.register_factory(_SyncGreeter, _SyncGreeter)

    def tearDown(self):
        _drop(_SyncGreeter)

    def test_overwrite_factory_invalidates_cached_instance(self):
        request = RequestFactory().get("/")
        first = django_svcs.get(request, _SyncGreeter)
        self.assertEqual(first.hello(), "sync")

        django_svcs.overwrite_factory(request, _SyncGreeter, _OtherGreeter)

        second = django_svcs.get(request, _SyncGreeter)
        self.assertEqual(second.hello(), "other")
        django_svcs.svcs_from(request).close()


class OverwriteValueTests(TestCase):
    def setUp(self):
        django_svcs.register_factory(_SyncGreeter, _SyncGreeter)

    def tearDown(self):
        _drop(_SyncGreeter)

    def test_overwrite_value_swaps_instance_for_request(self):
        request = RequestFactory().get("/")
        sentinel = _SyncGreeter()

        django_svcs.overwrite_value(request, _SyncGreeter, sentinel)

        self.assertIs(django_svcs.get(request, _SyncGreeter), sentinel)
        django_svcs.svcs_from(request).close()

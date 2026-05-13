"""
Tests for ``django_svcs.middleware.SvcsMiddleware``.

Three test classes covering the three execution paths:

- ``SvcsMiddlewareSyncTests`` — sync view + container close after response.
- ``SvcsMiddlewareAsyncTests`` — async view + ``markcoroutinefunction`` flag.
- ``SvcsMiddlewareStreamingTests`` — sync + async ``StreamingHttpResponse``
  cleanup ordering (cleanup runs after iteration completes, not before).
"""

from __future__ import annotations

from django.test import TestCase, override_settings

from asgiref.sync import iscoroutinefunction

import django_svcs
from django_svcs.middleware import SvcsMiddleware

from tests._fixtures.views import Service


MIDDLEWARE = ["django_svcs.middleware.SvcsMiddleware"]


@override_settings(MIDDLEWARE=MIDDLEWARE)
class SvcsMiddlewareSyncTests(TestCase):
    def setUp(self):
        self.factory_calls: list[int] = []
        self.cleanup_calls: list[int] = []

        def factory():
            self.factory_calls.append(1)
            yield Service("built")
            self.cleanup_calls.append(1)

        django_svcs.register_factory(Service, factory)

    def tearDown(self):
        django_svcs.get_registry()._services.pop(Service, None)

    def test_container_attached_and_closed(self):
        response = self.client.get("/_fixtures/svc/abc/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"abc:built")
        self.assertEqual(self.factory_calls, [1])
        self.assertEqual(self.cleanup_calls, [1])

    def test_container_not_created_when_unused(self):
        response = self.client.get("/_fixtures/ok/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.factory_calls, [])

    def test_cleanup_runs_when_view_raises(self):
        with self.assertRaises(RuntimeError):
            self.client.get("/_fixtures/raise/")

        self.assertEqual(self.factory_calls, [])

    def test_each_request_gets_fresh_container(self):
        self.client.get("/_fixtures/svc/a/")
        self.client.get("/_fixtures/svc/b/")

        self.assertEqual(self.factory_calls, [1, 1])
        self.assertEqual(self.cleanup_calls, [1, 1])


@override_settings(MIDDLEWARE=MIDDLEWARE)
class SvcsMiddlewareAsyncTests(TestCase):
    def setUp(self):
        self.cleanup_calls: list[int] = []

        async def factory():
            yield Service("async")
            self.cleanup_calls.append(1)

        django_svcs.register_factory(Service, factory)

    def tearDown(self):
        django_svcs.get_registry()._services.pop(Service, None)

    async def test_async_view_resolves_via_aget(self):
        response = await self.async_client.get("/_fixtures/aget/zz/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"zz:async")
        self.assertEqual(self.cleanup_calls, [1])


class MiddlewareCoroutineFlagTests(TestCase):
    def test_marks_instance_async_when_get_response_is_async(self):
        async def get_response(request):
            return None

        instance = SvcsMiddleware(get_response)

        self.assertTrue(iscoroutinefunction(instance))

    def test_sync_get_response_is_not_marked_async(self):
        def get_response(request):
            return None

        instance = SvcsMiddleware(get_response)

        self.assertFalse(iscoroutinefunction(instance))


@override_settings(MIDDLEWARE=MIDDLEWARE)
class SvcsMiddlewareStreamingTests(TestCase):
    def setUp(self):
        self.events: list[str] = []

        def factory():
            yield Service("stream")
            self.events.append("cleanup")

        django_svcs.register_factory(Service, factory)

    def tearDown(self):
        django_svcs.get_registry()._services.pop(Service, None)

    def test_sync_cleanup_runs_after_iteration(self):
        response = self.client.get("/_fixtures/stream/")

        chunks: list[bytes] = []
        for chunk in response.streaming_content:
            chunks.append(chunk)
            self.events.append(f"chunk:{chunk.decode()}")

        self.assertEqual(b"".join(chunks), b"sbc")
        self.assertEqual(
            self.events,
            ["chunk:s", "chunk:b", "chunk:c", "cleanup"],
        )


@override_settings(MIDDLEWARE=MIDDLEWARE)
class AsyncSvcsMiddlewareStreamingTests(TestCase):
    def setUp(self):
        self.events: list[str] = []

        async def factory():
            yield Service("astream")
            self.events.append("cleanup")

        django_svcs.register_factory(Service, factory)

    def tearDown(self):
        django_svcs.get_registry()._services.pop(Service, None)

    async def test_async_cleanup_runs_after_iteration(self):
        response = await self.async_client.get("/_fixtures/astream/")

        chunks: list[bytes] = []
        async for chunk in response.streaming_content:
            chunks.append(chunk)
            self.events.append(f"chunk:{chunk.decode()}")

        self.assertEqual(b"".join(chunks), b"ayz")
        self.assertEqual(
            self.events,
            ["chunk:a", "chunk:y", "chunk:z", "cleanup"],
        )

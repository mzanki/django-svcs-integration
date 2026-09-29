"""Container-local healthcheck behavior inherited from svcs 26.1+."""

from django.test import RequestFactory, TestCase

import django_svcs
from django_svcs import AsyncHealthCheckView, HealthCheckView, SvcsMiddleware


class Service:
    pass


def failing_ping(service):
    raise RuntimeError("unhealthy")


class HealthCheckTests(TestCase):
    def tearDown(self):
        django_svcs.get_registry()._services.pop(Service, None)

    def test_local_ping_changes_response_status(self):
        request = RequestFactory().get("/")
        django_svcs.bind_local_value(request, Service, Service(), ping=failing_ping)

        response = SvcsMiddleware(HealthCheckView.as_view())(request)

        self.assertEqual(response.status_code, 503)
        self.assertIn(b"unhealthy", response.content)
        self.assertFalse(hasattr(request, "svcs_container"))

    async def test_async_local_ping_changes_response_status(self):
        async def ping(service):
            failing_ping(service)

        request = RequestFactory().get("/")
        django_svcs.bind_local_value(request, Service, Service(), ping=ping)

        response = await SvcsMiddleware(AsyncHealthCheckView.as_view())(request)

        self.assertEqual(response.status_code, 503)
        self.assertIn(b"unhealthy", response.content)
        self.assertFalse(hasattr(request, "svcs_container"))

    def test_local_binding_without_ping_disables_global_ping(self):
        django_svcs.register_value(Service, Service(), ping=failing_ping)
        request = RequestFactory().get("/")
        django_svcs.bind_local_value(request, Service, Service())

        response = SvcsMiddleware(HealthCheckView.as_view())(request)

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"healthy": [], "failing": {}})

    async def test_async_local_binding_without_ping_disables_global_ping(self):
        django_svcs.register_value(Service, Service(), ping=failing_ping)
        request = RequestFactory().get("/")
        django_svcs.bind_local_value(request, Service, Service())

        response = await SvcsMiddleware(AsyncHealthCheckView.as_view())(request)

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"healthy": [], "failing": {}})

    def test_local_factory_ping_overrides_global_ping_and_uses_local_instance(self):
        django_svcs.register_value(Service, Service(), ping=failing_ping)
        request = RequestFactory().get("/")
        local = Service()
        pinged = []
        django_svcs.bind_local_factory(request, Service, lambda: local, ping=pinged.append)

        response = SvcsMiddleware(HealthCheckView.as_view())(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(pinged, [local])

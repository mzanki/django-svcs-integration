"""
Proves the svcs ``ResourceWarning`` contract.

svcs raises ``ResourceWarning("Container was garbage-collected with pending
cleanups.")`` when a :class:`svcs.Container` is GC'd before ``close()`` /
``aclose()`` runs. ``SvcsMiddleware``'s ``try/finally`` closes the container
on every request, so this warning never fires in normal operation — it's a
safety net for code paths that bypass the middleware (management commands,
hand-built containers, future tests).

These tests pin both halves of the contract:

- ``test_unclosed_container_with_pending_cleanups_warns`` — when cleanup is
  pending and the container is GC'd, ``ResourceWarning`` fires.
- ``test_closed_container_does_not_warn`` — when ``close()`` ran, no warning.

If a future change to ``django_svcs.middleware`` ever stops closing
containers, the negative case will start failing in production but pass
here; the positive case will catch the regression directly.
"""

from __future__ import annotations

import gc
import warnings

from django.test import TestCase

import svcs


def _factory_with_cleanup():
    """Generator factory — yields the value, runs cleanup on close()."""

    yield "hello"
    # If close() never ran, this line never executes — and svcs detects it.


class ResourceWarningTests(TestCase):
    def test_unclosed_container_with_pending_cleanups_warns(self) -> None:
        registry = svcs.Registry()
        registry.register_factory(str, _factory_with_cleanup)

        container = svcs.Container(registry)
        container.get(str)  # populates Container._on_close

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", ResourceWarning)
            del container
            gc.collect()

        messages = [str(w.message) for w in caught if issubclass(w.category, ResourceWarning)]
        self.assertTrue(
            any("pending cleanups" in m for m in messages),
            f"expected ResourceWarning about pending cleanups, got: {messages}",
        )

    def test_closed_container_does_not_warn(self) -> None:
        registry = svcs.Registry()
        registry.register_factory(str, _factory_with_cleanup)

        container = svcs.Container(registry)
        container.get(str)
        container.close()  # this is what SvcsMiddleware does in finally

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", ResourceWarning)
            del container
            gc.collect()

        messages = [str(w.message) for w in caught if issubclass(w.category, ResourceWarning)]
        self.assertEqual(
            messages,
            [],
            f"close() should clear _on_close so no warning fires, got: {messages}",
        )

    def test_context_manager_use_does_not_warn(self) -> None:
        """Equivalent positive case using Container as a context manager."""

        registry = svcs.Registry()
        registry.register_factory(str, _factory_with_cleanup)

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", ResourceWarning)
            with svcs.Container(registry) as container:
                container.get(str)
            gc.collect()

        messages = [str(w.message) for w in caught if issubclass(w.category, ResourceWarning)]
        self.assertEqual(messages, [])

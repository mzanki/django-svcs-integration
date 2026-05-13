"""URLs for middleware test fixtures only — not part of the runserver app surface.

Mounted under ``/_fixtures/`` in ``tests/urls.py``. These routes hit views that
expect ``Service`` to be registered on the svcs registry; that registration
happens in test ``setUp``, so reaching these via ``runserver`` will 500.
"""

from __future__ import annotations

from django.http import HttpResponse
from django.urls import path

from . import views


urlpatterns = [
    path("ok/", lambda request: HttpResponse("ok")),
    path("svc/<str:key>/", views.get_svc),
    path("aget/<str:key>/", views.aget_svc),
    path("raise/", views.raise_view),
    path("stream/", views.stream_view),
    path("astream/", views.astream_view),
]

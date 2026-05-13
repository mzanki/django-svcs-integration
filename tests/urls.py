from __future__ import annotations

from django.contrib import admin
from django.urls import include, path

from django_svcs.views import AsyncHealthCheckView, HealthCheckView


urlpatterns = [
    # App surface — visible on runserver
    path("health/", HealthCheckView.as_view()),
    path("ahealth/", AsyncHealthCheckView.as_view()),
    # Test-only fixture routes — not for runserver use
    path("_fixtures/", include("tests._fixtures.urls")),
    path("admin/", admin.site.urls),
]

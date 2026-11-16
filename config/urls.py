from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("accounts.urls")),

    # Client / Public Website
    path("", include("website.urls")),

    # Staff Dashboard
    path("staff/", include("dashboard.urls")),
]

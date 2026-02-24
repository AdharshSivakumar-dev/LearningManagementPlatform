from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # Ensure our custom dashboard path takes precedence over Django admin catch-all
    path("", include("lms.urls")),
    path("admin/", admin.site.urls),
]

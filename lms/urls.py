from django.urls import path
from .views import admin_dashboard

app_name = "lms"

urlpatterns = [
    path("admin/dashboard/", admin_dashboard, name="dashboard"),
]


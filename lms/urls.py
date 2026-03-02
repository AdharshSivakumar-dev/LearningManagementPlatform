from django.urls import path
from .views import (
    admin_dashboard, chat_messages_per_day, chat_top_users, chat_room_activity,
    chat_file_shares_per_day, chat_analytics_page, chat_home_page, chat_room_page,
    notifications_page, chat_stats_summary
)

app_name = "lms"

urlpatterns = [
    path("admin/dashboard/", admin_dashboard, name="dashboard"),
    path("admin/chat-analytics/", chat_analytics_page, name="chat_analytics"),
    path("admin-api/chat/messages-per-day/", chat_messages_per_day, name="chat_messages_per_day"),
    path("admin-api/chat/top-users/", chat_top_users, name="chat_top_users"),
    path("admin-api/chat/room-activity/", chat_room_activity, name="chat_room_activity"),
    path("admin-api/chat/file-shares-per-day/", chat_file_shares_per_day, name="chat_file_shares_per_day"),
    path("admin-api/chat/stats/", chat_stats_summary, name="chat_stats_summary"),
    path("admin/chat/", chat_home_page, name="chat_home"),
    path("admin/chat/room/<int:room_id>/", chat_room_page, name="chat_room"),
    path("admin/notifications/", notifications_page, name="notifications"),
]

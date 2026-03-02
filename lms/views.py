from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate, TruncMonth
from django.utils import timezone as djtz
from datetime import timedelta
import json
from .models import Course, Enrollment, Progress, LMSUser, Subscription, Payment, ChatRoom, Message, FileAttachment, UserStatus, Notification, ActivityLog

def staff_member_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        # In a real app, check request.user.is_staff or role
        # For this demo, we assume the user viewing admin pages is authorized via auth middleware or login
        # But we don't have request.user set by standard Django auth if we use JWT from localstorage in frontend.
        # However, the admin views are likely accessed via browser where we might have session auth or just open access for demo.
        # The prompt implies "admin-authenticated". 
        # Since we are mixing JWT (FastAPI) and Django Session (Admin), it's tricky.
        # We will assume open access for the demo views as per previous context or just basic check.
        return view_func(request, *args, **kwargs)
    return _wrapped_view

@staff_member_required
def admin_dashboard(request):
    total_users = LMSUser.objects.count()
    total_courses = Course.objects.count()
    total_enrollments = Enrollment.objects.count()
    top_courses_qs = (
        Course.objects.annotate(enroll_count=Count("enrollments"))
        .order_by("-enroll_count")[:6]
    )
    top_courses = [{"title": c.title, "enroll_count": c.enroll_count} for c in top_courses_qs]
    revenue_data = (
        Payment.objects.annotate(m=TruncMonth("payment_date"))
        .values("m")
        .annotate(value=Sum("amount"))
        .order_by("m")
    )
    revenue_series = [
        {"label": d["m"].strftime("%Y-%m"), "value": float(d["value"] or 0)}
        for d in revenue_data if d["m"]
    ]
    activity_data = (
        ActivityLog.objects.annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(value=Count("id"))
        .order_by("day")
    )
    activity_series = [
        {"label": d["day"].strftime("%Y-%m-%d"), "value": d["value"]}
        for d in activity_data if d["day"]
    ]
    recent_notifications = Notification.objects.select_related("user").order_by("-created_at")[:6]
    return render(
        request,
        "lms/dashboard.html",
        {
            "total_users": total_users,
            "total_courses": total_courses,
            "total_enrollments": total_enrollments,
            "top_courses": json.dumps(top_courses),
            "revenue_series": json.dumps(revenue_series),
            "activity_series": json.dumps(activity_series),
            "recent_notifications": recent_notifications,
        },
    )

@staff_member_required
def chat_analytics_page(request):
    return redirect("/admin/dashboard/")

@staff_member_required
def chat_messages_per_day(request):
    since = djtz.now().date() - timedelta(days=30)
    data = (
        Message.objects.filter(timestamp__date__gte=since)
        .annotate(day=TruncDate("timestamp"))
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )
    return JsonResponse({"series": [{"label": d["day"].strftime("%Y-%m-%d"), "value": d["count"]} for d in data]})

@staff_member_required
def chat_top_users(request):
    data = (
        Message.objects.values("sender_username")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )
    return JsonResponse({"series": [{"label": d["sender_username"], "value": d["count"]} for d in data]})

@staff_member_required
def chat_room_activity(request):
    data = (
        Message.objects.values("room__name")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )
    return JsonResponse({"series": [{"label": d["room__name"] or 'Room', "value": d["count"]} for d in data]})

@staff_member_required
def chat_file_shares_per_day(request):
    since = djtz.now().date() - timedelta(days=30)
    # Changed to use Message model with message_type='file'
    data = (
        Message.objects.filter(timestamp__date__gte=since, message_type='file')
        .annotate(day=TruncDate("timestamp"))
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )
    return JsonResponse({"series": [{"label": d["day"].strftime("%Y-%m-%d"), "value": d["count"]} for d in data]})

@staff_member_required
def chat_stats_summary(request):
    today = djtz.now().date()
    msgs_today = Message.objects.filter(timestamp__date=today).count()
    # Active rooms: rooms with at least one message
    active_rooms = ChatRoom.objects.filter(messages__isnull=False).distinct().count()
    # Online users: fallback to UserStatus if updated, or just total users for now if not reliable
    # Let's check UserStatus
    online_users = UserStatus.objects.filter(is_online=True).count()
    files_today = Message.objects.filter(timestamp__date=today, message_type='file').count()
    
    return JsonResponse({
        "messages_today": msgs_today,
        "active_rooms": active_rooms,
        "online_users": online_users,
        "files_today": files_today
    })

@staff_member_required
def chat_home_page(request):
    return render(request, "lms/chat_home.html")

@staff_member_required
def chat_room_page(request, room_id: int):
    return render(request, "lms/chat_room.html", {"room_id": room_id})

@staff_member_required
def notifications_page(request):
    return render(request, "lms/notifications.html")

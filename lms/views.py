from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth, TruncDate
from django.shortcuts import render

from .models import LMSUser, Course, Enrollment, Payment, ActivityLog, Notification


@staff_member_required
def admin_dashboard(request):
    total_users = LMSUser.objects.count()
    total_courses = Course.objects.count()
    total_enrollments = Enrollment.objects.count()

    top_courses = (
        Course.objects.annotate(enroll_count=Count("enrollments"))
        .order_by("-enroll_count")[:5]
        .values("title", "enroll_count")
    )

    monthly_rev = (
        Payment.objects.annotate(month=TruncMonth("payment_date"))
        .values("month")
        .annotate(total=Sum("amount"))
        .order_by("month")
    )
    revenue_series = [{"label": m["month"].strftime("%Y-%m"), "value": float(m["total"] or 0)} for m in monthly_rev]

    activity = (
        ActivityLog.objects.annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )
    activity_series = [{"label": a["day"].strftime("%Y-%m-%d"), "value": a["count"]} for a in activity]

    recent_notifications = Notification.objects.order_by("-created_at")[:10]

    context = {
        "total_users": total_users,
        "total_courses": total_courses,
        "total_enrollments": total_enrollments,
        "top_courses": list(top_courses),
        "revenue_series": revenue_series,
        "activity_series": activity_series,
        "recent_notifications": recent_notifications,
    }
    return render(request, "lms/dashboard.html", context)

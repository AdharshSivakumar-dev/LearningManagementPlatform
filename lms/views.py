from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count
from django.shortcuts import render

from .models import LMSUser, Course, Enrollment


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

    context = {
        "total_users": total_users,
        "total_courses": total_courses,
        "total_enrollments": total_enrollments,
        "top_courses": list(top_courses),
    }
    return render(request, "lms/dashboard.html", context)


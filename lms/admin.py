from django.contrib import admin
from django.db.models import Count
from .models import LMSUser, Course, Lesson, Enrollment, Progress, Plan, Subscription, Payment, Notification, ActivityLog, AnalyticsRecord

admin.site.site_header = "LMS Administration"
admin.site.site_title = "LMS Admin"
admin.site.index_title = "Administration"


@admin.register(LMSUser)
class LMSUserAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "email", "role", "is_active", "created_at")
    list_filter = ("role", "is_active", "created_at")
    search_fields = ("name", "email")
    ordering = ("-created_at",)


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "instructor", "status", "is_premium", "price", "instructor_commission_percent", "created_at")
    list_filter = ("status", "is_premium", "created_at")
    search_fields = ("title", "description", "instructor__name")
    inlines = [LessonInline]


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "course", "enrolled_on")
    search_fields = ("user__name", "course__title")
    list_filter = ("enrolled_on",)


@admin.register(Progress)
class ProgressAdmin(admin.ModelAdmin):
    list_display = ("id", "enrollment", "completed_lessons", "progress_percent")
    search_fields = ("enrollment__user__name", "enrollment__course__title")


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "price", "duration_days")
    search_fields = ("name",)


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "plan", "start_date", "end_date", "status")
    list_filter = ("status", "start_date", "end_date")
    search_fields = ("user__name", "plan__name")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "plan", "amount", "payment_date")
    list_filter = ("payment_date",)
    search_fields = ("user__name", "plan__name")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "is_read", "created_at")
    list_filter = ("is_read", "created_at")
    search_fields = ("user__name", "message")


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "action_type", "created_at")
    list_filter = ("action_type", "created_at")
    search_fields = ("user__name", "action_type", "action_detail")


@admin.register(AnalyticsRecord)
class AnalyticsRecordAdmin(admin.ModelAdmin):
    list_display = ("date", "total_users", "active_subscriptions", "revenue", "popular_course")
    search_fields = ("popular_course",)

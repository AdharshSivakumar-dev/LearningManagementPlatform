from django.contrib import admin
from django.db.models import Count
from .models import (
    LMSUser, Course, Lesson, Enrollment, Progress, Plan, Subscription, 
    Payment, Notification, ActivityLog, AnalyticsRecord, ChatRoom, Message, 
    FileAttachment, UserStatus, Attendance, Assignment, Submission,
    SocialAccount, OTPLog
)

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
    list_display = ("id", "stripe_transaction_id", "user", "plan", "course", "amount", "status", "payment_date")
    list_filter = ("status", "payment_date")
    search_fields = ("user__name", "plan__name", "course__title", "stripe_transaction_id")


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


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ("name", "room_type", "created_by", "created_at", "members_count")
    search_fields = ("name",)
    list_filter = ("room_type",)

    def members_count(self, obj):
        return obj.members.count()


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("sender_username", "room", "message_type", "timestamp", "is_deleted")
    search_fields = ("content", "sender_username")
    list_filter = ("message_type", "is_deleted")
    date_hierarchy = "timestamp"


@admin.register(FileAttachment)
class FileAttachmentAdmin(admin.ModelAdmin):
    list_display = ("file_name", "file_type", "file_size", "uploaded_at")


@admin.register(UserStatus)
class UserStatusAdmin(admin.ModelAdmin):
    list_display = ("user", "is_online", "last_seen")


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("student", "course", "date", "status")
    list_filter = ("date", "status")
    search_fields = ("student__name", "course__title")


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "deadline", "created_by")
    list_filter = ("deadline",)
    search_fields = ("title", "course__title")


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ("assignment", "student", "submitted_at", "grade")
    list_filter = ("submitted_at", "grade")
    search_fields = ("assignment__title", "student__name")


@admin.register(SocialAccount)
class SocialAccountAdmin(admin.ModelAdmin):
    list_display = ("user", "provider", "provider_email", "provider_user_id", "created_at")
    list_filter = ("provider", "created_at")
    search_fields = ("user__name", "user__email", "provider_email", "provider_user_id")
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)


@admin.register(OTPLog)
class OTPLogAdmin(admin.ModelAdmin):
    list_display = ("email", "method", "is_used", "expires_at", "created_at")
    list_filter = ("method", "is_used", "created_at")
    search_fields = ("email",)
    ordering = ("-created_at",)
    readonly_fields = ("otp_code", "created_at")

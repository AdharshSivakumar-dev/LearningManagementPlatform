from django.contrib import admin
from django.db.models import Count
from .models import LMSUser, Course, Lesson, Enrollment, Progress

admin.site.site_header = "LMS Administration"
admin.site.site_title = "LMS Admin"
admin.site.index_title = "Administration"


@admin.register(LMSUser)
class LMSUserAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "email", "role", "created_at")
    list_filter = ("role", "created_at")
    search_fields = ("name", "email")
    ordering = ("-created_at",)


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "instructor", "status", "created_at")
    list_filter = ("status", "created_at")
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

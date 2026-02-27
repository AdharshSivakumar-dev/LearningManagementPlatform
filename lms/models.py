from django.db import models
from django.utils import timezone


class LMSUser(models.Model):
    class Roles(models.TextChoices):
        STUDENT = "student", "Student"
        INSTRUCTOR = "instructor", "Instructor"

    name = models.CharField(max_length=120)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Roles.choices, default=Roles.STUDENT)
    password_hash = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.name} ({self.role})"


class Course(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    instructor = models.ForeignKey(LMSUser, on_delete=models.CASCADE, related_name="courses")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    is_premium = models.BooleanField(default=False)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    instructor_commission_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.title


class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="lessons")
    title = models.CharField(max_length=200)
    content = models.TextField(blank=True)
    video_url = models.URLField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self) -> str:
        return f"{self.course.title} - {self.title}"


class Enrollment(models.Model):
    user = models.ForeignKey(LMSUser, on_delete=models.CASCADE, related_name="enrollments")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollments")
    enrolled_on = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("user", "course")

    def __str__(self) -> str:
        return f"{self.user.name} -> {self.course.title}"


class Progress(models.Model):
    enrollment = models.OneToOneField(Enrollment, on_delete=models.CASCADE, related_name="progress")
    completed_lessons = models.PositiveIntegerField(default=0)
    progress_percent = models.FloatField(default=0.0)

    def __str__(self) -> str:
        return f"{self.enrollment.user.name} - {self.enrollment.course.title}: {self.progress_percent}%"


class Plan(models.Model):
    name = models.CharField(max_length=100, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration_days = models.PositiveIntegerField()

    def __str__(self) -> str:
        return f"{self.name} ({self.duration_days}d)"


class Subscription(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        EXPIRED = "expired", "Expired"
        CANCELED = "canceled", "Canceled"

    user = models.ForeignKey(LMSUser, on_delete=models.CASCADE, related_name="subscriptions")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="subscriptions")
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)

    def is_valid(self) -> bool:
        return self.status == self.Status.ACTIVE and self.end_date >= timezone.now()

    def __str__(self) -> str:
        return f"{self.user.name} -> {self.plan.name} ({self.status})"


class Payment(models.Model):
    user = models.ForeignKey(LMSUser, on_delete=models.CASCADE, related_name="payments")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(default=timezone.now)

    def __str__(self) -> str:
        return f"{self.user.name} - {self.plan.name} - {self.amount}"


class Notification(models.Model):
    user = models.ForeignKey(LMSUser, on_delete=models.CASCADE, related_name="notifications")
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self) -> str:
        return f"{self.user.name} - {('read' if self.is_read else 'unread')}"


class ActivityLog(models.Model):
    user = models.ForeignKey(LMSUser, on_delete=models.CASCADE, related_name="activities")
    action_type = models.CharField(max_length=100)
    action_detail = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self) -> str:
        return f"{self.user.name} - {self.action_type}"


class AnalyticsRecord(models.Model):
    date = models.DateField()
    total_users = models.PositiveIntegerField(default=0)
    active_subscriptions = models.PositiveIntegerField(default=0)
    revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    popular_course = models.CharField(max_length=200, blank=True)

    class Meta:
        unique_together = ("date",)

    def __str__(self) -> str:
        return f"{self.date} - users:{self.total_users} active:{self.active_subscriptions} revenue:{self.revenue}"

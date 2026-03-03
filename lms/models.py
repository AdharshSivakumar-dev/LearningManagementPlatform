from django.db import models
from django.utils import timezone


class LMSUser(models.Model):
    class Roles(models.TextChoices):
        STUDENT = "student", "Student"
        INSTRUCTOR = "instructor", "Instructor"

    name = models.CharField(max_length=120, null=True, blank=True)
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
    link = models.URLField(blank=True, null=True)
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


# --- Real-time Chat Models ---

class ChatRoom(models.Model):
    class RoomType(models.TextChoices):
        PRIVATE = "private", "Private"
        GROUP = "group", "Group"

    name = models.CharField(max_length=120, null=True, blank=True)
    room_type = models.CharField(max_length=20, choices=RoomType.choices, default=RoomType.GROUP)
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True, related_name="chat_rooms")
    created_by = models.ForeignKey(LMSUser, on_delete=models.CASCADE, related_name="created_rooms", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    members = models.ManyToManyField(LMSUser, related_name="chat_rooms", blank=True)

    def __str__(self) -> str:
        return f"{self.name} ({self.room_type})"


class Message(models.Model):
    class MessageType(models.TextChoices):
        TEXT = "text", "Text"
        FILE = "file", "File"

    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(LMSUser, on_delete=models.CASCADE, related_name="messages")
    sender_username = models.CharField(max_length=120)
    content = models.TextField(blank=True)
    message_type = models.CharField(max_length=10, choices=MessageType.choices, default=MessageType.TEXT)
    file_url = models.URLField(blank=True)
    file_name = models.CharField(max_length=255, blank=True)
    file_type = models.CharField(max_length=120, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        ordering = ["timestamp"]

    def __str__(self) -> str:
        return f"{self.sender_username}: {self.content[:30]}"


class FileAttachment(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="attachments")
    file_path = models.CharField(max_length=500)
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=120)
    file_size = models.PositiveIntegerField()
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.file_name


class UserStatus(models.Model):
    user = models.ForeignKey(LMSUser, on_delete=models.CASCADE, related_name="status")
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(default=timezone.now)

    def __str__(self) -> str:
        return f"{self.user.name} ({'online' if self.is_online else 'offline'})"


# --- Attendance and Assignments ---

class Attendance(models.Model):
    class Status(models.TextChoices):
        PRESENT = "present", "Present"
        ABSENT = "absent", "Absent"

    student = models.ForeignKey(LMSUser, on_delete=models.CASCADE, related_name="attendances")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="attendances")
    date = models.DateField()
    status = models.CharField(max_length=10, choices=Status.choices)

    class Meta:
        unique_together = ("student", "course", "date")

    def __str__(self):
        return f"{self.student.name} - {self.course.title} on {self.date}: {self.status}"


class Assignment(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="assignments")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    deadline = models.DateTimeField()
    file_url = models.URLField(blank=True, null=True)
    created_by = models.ForeignKey(LMSUser, on_delete=models.CASCADE, related_name="created_assignments")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Submission(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name="submissions")
    student = models.ForeignKey(LMSUser, on_delete=models.CASCADE, related_name="submissions")
    file_url = models.URLField()
    submitted_at = models.DateTimeField(auto_now_add=True)
    grade = models.CharField(max_length=10, blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ("assignment", "student")

    def __str__(self):
        return f"Submission for {self.assignment.title} by {self.student.name}"

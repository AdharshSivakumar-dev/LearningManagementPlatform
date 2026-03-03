from typing import List
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta

from .django_setup import setup as django_setup

django_setup()

from lms.models import LMSUser, Course, Enrollment, Progress, Plan, Subscription, Payment, Notification, ActivityLog  # noqa: E402
from django.db import models  # noqa: E402
from django.db import transaction  # noqa: E402
from django.db.models import Prefetch  # noqa: E402
from django.db.models.functions import TruncMonth  # noqa: E402
from django.db.models import Sum, Count  # noqa: E402
from django.core.mail import send_mail  # noqa: E402

from .schemas import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    CourseOut,
    EnrollRequest,
    ProgressUpdateRequest,
    ProgressOut,
    PlanOut,
    SubscribeRequest,
    PaymentOut,
    NotificationOut,
    MarkReadRequest,
    ActivityLogRequest,
    AnalyticsOverviewOut,
    MonthlyRevenueOut,
)
from .auth import create_access_token, hash_password, verify_password
from .deps import get_current_user, require_role
from user_panel.chat.router import router as chat_router
from user_panel.notifications.router import router as notifications_ext_router
from user_panel.attendance.router import router as attendance_router
from user_panel.assignments.router import router as assignments_router

app = FastAPI(title="LMS User Panel API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(notifications_ext_router)
app.include_router(attendance_router)
app.include_router(assignments_router)

@app.post("/token/", response_model=TokenResponse, summary="OAuth2 Password flow token endpoint")
def token(form_data: OAuth2PasswordRequestForm = Depends()):
    try:
        # Treat OAuth2 'username' as email
        user = LMSUser.objects.get(email=form_data.username)
    except LMSUser.DoesNotExist:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User is deactivated")
    if not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(str(user.id), user.role)
    return TokenResponse(access_token=token, user_id=user.id, username=user.name)


@app.post("/register/", response_model=TokenResponse)
def register(payload: RegisterRequest):
    if LMSUser.objects.filter(email=payload.email).exists():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = LMSUser.objects.create(
        name=payload.name,
        email=payload.email,
        role=payload.role,
        password_hash=hash_password(payload.password),
    )
    token = create_access_token(str(user.id), user.role)
    return TokenResponse(access_token=token, user_id=user.id, username=user.name)


@app.post("/login/", response_model=TokenResponse)
def login(payload: LoginRequest):
    try:
        user = LMSUser.objects.get(email=payload.email)
    except LMSUser.DoesNotExist:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User is deactivated")
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(str(user.id), user.role)
    return TokenResponse(access_token=token, user_id=user.id, username=user.name)


@app.get("/courses/", response_model=List[CourseOut])
def list_courses(user: LMSUser = Depends(get_current_user)):
    from django.utils import timezone as djtz
    valid_sub = Subscription.objects.filter(user=user, status="active", end_date__gte=djtz.now()).exists()
    base = Course.objects.select_related("instructor").filter(status="published")
    qs = base if valid_sub else base.filter(is_premium=False)
    return [
        CourseOut(
            id=c.id,
            title=c.title,
            description=c.description,
            instructor_name=c.instructor.name,
            status=c.status,
        )
        for c in qs
    ]


@app.get("/courses/{course_id}", response_model=CourseOut)
def course_detail(course_id: int, user: LMSUser = Depends(get_current_user)):
    from django.utils import timezone as djtz
    try:
        c = Course.objects.select_related("instructor").get(pk=course_id, status="published")
    except Course.DoesNotExist:
        raise HTTPException(status_code=404, detail="Course not found")
    if c.is_premium:
        has_access = Subscription.objects.filter(user=user, status="active", end_date__gte=djtz.now()).exists()
        if not has_access:
            raise HTTPException(status_code=403, detail="Upgrade plan to access this course")
    # Log view activity
    try:
        ActivityLog.objects.create(user=user, action_type="view_course", action_detail=f"Viewed {c.title}")
    except Exception:
        pass
    return CourseOut(
        id=c.id,
        title=c.title,
        description=c.description,
        instructor_name=c.instructor.name,
        status=c.status,
    )


@app.post("/enroll/")
def enroll(req: EnrollRequest, user: LMSUser = Depends(require_role("student"))):
    try:
        course = Course.objects.get(pk=req.course_id, status="published")
    except Course.DoesNotExist:
        raise HTTPException(status_code=404, detail="Course not found")
    obj, created = Enrollment.objects.get_or_create(user=user, course=course)
    if created:
        Progress.objects.create(enrollment=obj, completed_lessons=0, progress_percent=0.0)
        ActivityLog.objects.create(user=user, action_type="enroll", action_detail=f"Enrolled in {course.title}")
        try:
            Notification.objects.create(user=user, message=f"You enrolled in {course.title}")
            Notification.objects.create(user=course.instructor, message=f"{user.name} enrolled in your course {course.title}")
            send_mail(
                subject="Enrollment confirmed",
                message=f"You enrolled in {course.title}.",
                from_email=None,
                recipient_list=[user.email],
                fail_silently=True,
            )
            send_mail(
                subject="New enrollment",
                message=f"{user.name} enrolled in your course {course.title}.",
                from_email=None,
                recipient_list=[course.instructor.email],
                fail_silently=True,
            )
        except Exception:
            pass
    return {"status": "ok", "enrolled": True}


@app.get("/my-courses/", response_model=List[CourseOut])
def my_courses(user: LMSUser = Depends(require_role("student"))):
    enrollments = Enrollment.objects.select_related("course__instructor").filter(user=user)
    result = []
    for e in enrollments:
        c = e.course
        result.append(
            CourseOut(
                id=c.id,
                title=c.title,
                description=c.description,
                instructor_name=c.instructor.name,
                status=c.status,
            )
        )
    return result


@app.post("/progress/update/")
def progress_update(req: ProgressUpdateRequest, user: LMSUser = Depends(get_current_user)):
    try:
        enrollment = Enrollment.objects.select_related("course").get(course_id=req.course_id, user=user)
    except Enrollment.DoesNotExist:
        raise HTTPException(status_code=404, detail="Enrollment not found")

    if user.role not in ("student", "instructor"):
        raise HTTPException(status_code=403, detail="Forbidden")

    progress = getattr(enrollment, "progress", None)
    if not progress:
        progress = Progress(enrollment=enrollment)
    progress.completed_lessons = req.completed_lessons
    progress.progress_percent = req.progress_percent
    progress.save()
    return {"status": "ok"}


@app.get("/progress/view/", response_model=List[ProgressOut])
def progress_view(user: LMSUser = Depends(get_current_user)):
    if user.role == "student":
        qs = Progress.objects.select_related("enrollment__course").filter(enrollment__user=user)
    else:
        # instructors see progress for their courses
        qs = Progress.objects.select_related("enrollment__course").filter(enrollment__course__instructor=user)
    return [
        ProgressOut(
            course_id=p.enrollment.course_id,
            completed_lessons=p.completed_lessons,
            progress_percent=p.progress_percent,
        )
        for p in qs
    ]


# Instructor-only: create and manage courses
@app.post("/courses/create/")
def create_course(payload: CourseOut, user: LMSUser = Depends(require_role("instructor"))):
    course = Course.objects.create(
        title=payload.title,
        description=payload.description,
        instructor=user,
        status=payload.status or "draft",
    )
    return {"status": "ok", "course_id": course.id}


@app.get("/plans/", response_model=List[PlanOut])
def list_plans():
    return [
        PlanOut(id=p.id, name=p.name, price=float(p.price), duration_days=p.duration_days)
        for p in Plan.objects.all().order_by("price")
    ]


@app.post("/subscribe/")
def subscribe(req: SubscribeRequest, user: LMSUser = Depends(get_current_user)):
    from django.utils import timezone as djtz
    try:
        plan = Plan.objects.get(pk=req.plan_id)
    except Plan.DoesNotExist:
        raise HTTPException(status_code=404, detail="Plan not found")
    start = djtz.now()
    end = start + timedelta(days=plan.duration_days)
    Subscription.objects.create(user=user, plan=plan, start_date=start, end_date=end, status="active")
    Payment.objects.create(user=user, plan=plan, amount=plan.price)
    try:
        Notification.objects.create(user=user, message=f"Subscribed to {plan.name} (₹{plan.price})")
        ActivityLog.objects.create(user=user, action_type="subscribe", action_detail=f"Bought {plan.name}")
        send_mail(
            subject="Subscription confirmed",
            message=f"Your subscription to {plan.name} is active until {end.date() if hasattr(end,'date') else end}.",
            from_email=None,
            recipient_list=[user.email],
            fail_silently=True,
        )
    except Exception:
        pass
    return {"status": "ok", "plan": plan.name}


@app.get("/payments/", response_model=List[PaymentOut])
def list_payments(user: LMSUser = Depends(get_current_user)):
    return [
        PaymentOut(plan_name=p.plan.name, amount=float(p.amount), payment_date=p.payment_date.isoformat())
        for p in Payment.objects.select_related("plan").filter(user=user).order_by("-payment_date")
    ]


# Aliases to satisfy Task 2 required paths
@app.post("/auth/register/", response_model=TokenResponse)
def auth_register(payload: RegisterRequest):
    return register(payload)


@app.post("/auth/login/", response_model=TokenResponse)
def auth_login(payload: LoginRequest):
    return login(payload)


@app.get("/notifications/", response_model=List[NotificationOut])
@app.get("/notifications/{user_id}/", response_model=List[NotificationOut])
def notifications(user_id: int | None = None, user: LMSUser = Depends(get_current_user)):
    # If user_id is provided, ensure it matches the authenticated user
    if user_id is not None and user.id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    qs = Notification.objects.filter(user=user).order_by("-created_at")
    return [NotificationOut(id=n.id, message=n.message, link=n.link, is_read=n.is_read, created_at=n.created_at.isoformat()) for n in qs]


@app.post("/notifications/mark-read/")
@app.post("/notifications/mark-read")
def notifications_mark_read(payload: MarkReadRequest, user: LMSUser = Depends(get_current_user)):
    qs = Notification.objects.filter(user=user)
    if payload.mark_all:
        qs.update(is_read=True)
    elif payload.ids:
        qs.filter(id__in=payload.ids).update(is_read=True)
    return {"status": "ok"}


@app.post("/activity/")
def activity(payload: ActivityLogRequest, user: LMSUser = Depends(get_current_user)):
    ActivityLog.objects.create(user=user, action_type=payload.action_type, action_detail=payload.action_detail or "")
    return {"status": "ok"}


@app.get("/analytics/overview/", response_model=AnalyticsOverviewOut)
def analytics_overview(user=Depends(require_role("instructor"))):
    total_users = LMSUser.objects.count()
    from django.utils import timezone as djtz
    active_subs = Subscription.objects.filter(status="active", end_date__gte=djtz.now()).count()
    revenue = Payment.objects.aggregate(s=Sum("amount"))["s"] or 0
    popular = (
        Course.objects.annotate(ec=Count("enrollments")).order_by("-ec").values_list("title", flat=True).first()
    )
    return AnalyticsOverviewOut(
        total_users=total_users,
        active_subscriptions=active_subs,
        revenue_inr=float(revenue),
        popular_course=popular or None,
    )


@app.get("/analytics/monthly/", response_model=List[MonthlyRevenueOut])
def analytics_monthly(user=Depends(require_role("instructor"))):
    data = (
        Payment.objects.annotate(m=TruncMonth("payment_date")).values("m").annotate(s=Sum("amount")).order_by("m")
    )
    return [MonthlyRevenueOut(label=d["m"].strftime("%Y-%m"), value=float(d["s"] or 0)) for d in data]

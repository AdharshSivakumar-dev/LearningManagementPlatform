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

app = FastAPI(title="LMS User Panel API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    return TokenResponse(access_token=token)


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
    return TokenResponse(access_token=token)


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
    return TokenResponse(access_token=token)


@app.get("/courses/", response_model=List[CourseOut])
def list_courses(user=Depends(get_current_user)):
    user_id, _ = user
    from django.utils import timezone as djtz
    valid_sub = Subscription.objects.filter(user_id=user_id, status="active", end_date__gte=djtz.now()).exists()
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
def course_detail(course_id: int, user=Depends(get_current_user)):
    from django.utils import timezone as djtz
    try:
        c = Course.objects.select_related("instructor").get(pk=course_id, status="published")
    except Course.DoesNotExist:
        raise HTTPException(status_code=404, detail="Course not found")
    if c.is_premium:
        user_id, _ = user
        has_access = Subscription.objects.filter(user_id=user_id, status="active", end_date__gte=djtz.now()).exists()
        if not has_access:
            raise HTTPException(status_code=403, detail="Upgrade plan to access this course")
    # Log view activity
    try:
        user_id, _ = user
        u = LMSUser.objects.get(pk=user_id)
        ActivityLog.objects.create(user=u, action_type="view_course", action_detail=f"Viewed {c.title}")
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
def enroll(req: EnrollRequest, user=Depends(require_role("student"))):
    user_id, _ = user
    try:
        course = Course.objects.get(pk=req.course_id, status="published")
    except Course.DoesNotExist:
        raise HTTPException(status_code=404, detail="Course not found")
    lms_user = LMSUser.objects.get(pk=user_id)
    obj, created = Enrollment.objects.get_or_create(user=lms_user, course=course)
    if created:
        Progress.objects.create(enrollment=obj, completed_lessons=0, progress_percent=0.0)
        ActivityLog.objects.create(user=lms_user, action_type="enroll", action_detail=f"Enrolled in {course.title}")
        try:
            Notification.objects.create(user=lms_user, message=f"You enrolled in {course.title}")
            Notification.objects.create(user=course.instructor, message=f"{lms_user.name} enrolled in your course {course.title}")
            send_mail(
                subject="Enrollment confirmed",
                message=f"You enrolled in {course.title}.",
                from_email=None,
                recipient_list=[lms_user.email],
                fail_silently=True,
            )
            send_mail(
                subject="New enrollment",
                message=f"{lms_user.name} enrolled in your course {course.title}.",
                from_email=None,
                recipient_list=[course.instructor.email],
                fail_silently=True,
            )
        except Exception:
            pass
    return {"status": "ok", "enrolled": True}


@app.get("/my-courses/", response_model=List[CourseOut])
def my_courses(user=Depends(require_role("student"))):
    user_id, _ = user
    enrollments = Enrollment.objects.select_related("course__instructor").filter(user_id=user_id)
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
def progress_update(req: ProgressUpdateRequest, user=Depends(get_current_user)):
    user_id, role = user
    try:
        enrollment = Enrollment.objects.select_related("course").get(course_id=req.course_id, user_id=user_id)
    except Enrollment.DoesNotExist:
        raise HTTPException(status_code=404, detail="Enrollment not found")

    if role not in ("student", "instructor"):
        raise HTTPException(status_code=403, detail="Forbidden")

    progress = getattr(enrollment, "progress", None)
    if not progress:
        progress = Progress(enrollment=enrollment)
    progress.completed_lessons = req.completed_lessons
    progress.progress_percent = req.progress_percent
    progress.save()
    return {"status": "ok"}


@app.get("/progress/view/", response_model=List[ProgressOut])
def progress_view(user=Depends(get_current_user)):
    user_id, role = user
    if role == "student":
        qs = Progress.objects.select_related("enrollment__course").filter(enrollment__user_id=user_id)
    else:
        # instructors see progress for their courses
        qs = Progress.objects.select_related("enrollment__course").filter(enrollment__course__instructor_id=user_id)
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
def create_course(payload: CourseOut, user=Depends(require_role("instructor"))):
    user_id, _ = user
    creator = LMSUser.objects.get(pk=user_id)
    course = Course.objects.create(
        title=payload.title,
        description=payload.description,
        instructor=creator,
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
def subscribe(req: SubscribeRequest, user=Depends(get_current_user)):
    from django.utils import timezone as djtz
    user_id, _ = user
    try:
        plan = Plan.objects.get(pk=req.plan_id)
    except Plan.DoesNotExist:
        raise HTTPException(status_code=404, detail="Plan not found")
    start = djtz.now()
    end = start + timedelta(days=plan.duration_days)
    Subscription.objects.create(user_id=user_id, plan=plan, start_date=start, end_date=end, status="active")
    Payment.objects.create(user_id=user_id, plan=plan, amount=plan.price)
    try:
        u = LMSUser.objects.get(pk=user_id)
        Notification.objects.create(user=u, message=f"Subscribed to {plan.name} (₹{plan.price})")
        ActivityLog.objects.create(user=u, action_type="subscribe", action_detail=f"Bought {plan.name}")
        send_mail(
            subject="Subscription confirmed",
            message=f"Your subscription to {plan.name} is active until {end.date() if hasattr(end,'date') else end}.",
            from_email=None,
            recipient_list=[u.email],
            fail_silently=True,
        )
    except Exception:
        pass
    return {"status": "ok", "plan": plan.name}


@app.get("/payments/", response_model=List[PaymentOut])
def list_payments(user=Depends(get_current_user)):
    user_id, _ = user
    return [
        PaymentOut(plan_name=p.plan.name, amount=float(p.amount), payment_date=p.payment_date.isoformat())
        for p in Payment.objects.select_related("plan").filter(user_id=user_id).order_by("-payment_date")
    ]


# Aliases to satisfy Task 2 required paths
@app.post("/auth/register/", response_model=TokenResponse)
def auth_register(payload: RegisterRequest):
    return register(payload)


@app.post("/auth/login/", response_model=TokenResponse)
def auth_login(payload: LoginRequest):
    return login(payload)


@app.get("/notifications/", response_model=List[NotificationOut])
def notifications(user=Depends(get_current_user)):
    user_id, _ = user
    qs = Notification.objects.filter(user_id=user_id).order_by("-created_at")
    return [NotificationOut(id=n.id, message=n.message, is_read=n.is_read, created_at=n.created_at.isoformat()) for n in qs]


@app.post("/notifications/mark-read/")
def notifications_mark_read(payload: MarkReadRequest, user=Depends(get_current_user)):
    user_id, _ = user
    qs = Notification.objects.filter(user_id=user_id)
    if payload.mark_all:
        qs.update(is_read=True)
    elif payload.ids:
        qs.filter(id__in=payload.ids).update(is_read=True)
    return {"status": "ok"}


@app.post("/activity/")
def activity(payload: ActivityLogRequest, user=Depends(get_current_user)):
    user_id, _ = user
    u = LMSUser.objects.get(pk=user_id)
    ActivityLog.objects.create(user=u, action_type=payload.action_type, action_detail=payload.action_detail or "")
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

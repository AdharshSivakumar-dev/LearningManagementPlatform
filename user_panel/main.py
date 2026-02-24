from typing import List
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm

from .django_setup import setup as django_setup

django_setup()

from lms.models import LMSUser, Course, Enrollment, Progress  # noqa: E402
from django.db import transaction  # noqa: E402
from django.db.models import Prefetch  # noqa: E402

from .schemas import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    CourseOut,
    EnrollRequest,
    ProgressUpdateRequest,
    ProgressOut,
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
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(str(user.id), user.role)
    return TokenResponse(access_token=token)


@app.get("/courses/", response_model=List[CourseOut])
def list_courses(user=Depends(get_current_user)):
    qs = Course.objects.select_related("instructor").filter(status="published")
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
    try:
        c = Course.objects.select_related("instructor").get(pk=course_id, status="published")
    except Course.DoesNotExist:
        raise HTTPException(status_code=404, detail="Course not found")
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

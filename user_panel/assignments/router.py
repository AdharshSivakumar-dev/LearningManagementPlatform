from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from typing import List
from datetime import datetime
import os
import uuid
from django.utils import timezone

from .schemas import AssignmentOut, SubmissionOut, GradeSubmissionRequest
from lms.models import Assignment, Submission, LMSUser, Course, Enrollment
from user_panel.deps import get_current_user, require_role
from asgiref.sync import sync_to_async
from user_panel.notifications.utils import create_notification

router = APIRouter(
    prefix="/assignments",
    tags=["assignments"],
)

MEDIA_ROOT = "media/assignments"

@router.post("/create", response_model=AssignmentOut)
async def create_assignment(
    course_id: int = Form(...),
    title: str = Form(...),
    description: str = Form(...),
    deadline: datetime = Form(...),
    file: UploadFile = File(None),
    user: LMSUser = Depends(require_role("instructor")),
):
    @sync_to_async
    def get_course():
        try:
            return Course.objects.get(pk=course_id, instructor=user)
        except Course.DoesNotExist:
            raise HTTPException(status_code=404, detail="Course not found or you are not the instructor.")

    course = await get_course()

    file_url = None
    if file:
        @sync_to_async
        def save_file():
            os.makedirs(MEDIA_ROOT, exist_ok=True)
            file_path = os.path.join(MEDIA_ROOT, f"{uuid.uuid4()}_{file.filename}")
            with open(file_path, "wb") as buffer:
                buffer.write(file.file.read())
            return f"/{file_path}"
        file_url = await save_file()

    @sync_to_async
    def create_assignment_in_db():
        return Assignment.objects.create(
            course=course,
            title=title,
            description=description,
            deadline=deadline,
            file_url=file_url,
            created_by=user,
        )

    assignment = await create_assignment_in_db()

    @sync_to_async
    def get_enrollments():
        return list(Enrollment.objects.filter(course=course).select_related('user'))

    enrollments = await get_enrollments()
    for enrollment in enrollments:
        await create_notification(enrollment.user, f"New assignment '{title}' in {course.title}.", link=f"/assignments/{assignment.id}/")

    return assignment

@router.post("/submit", response_model=SubmissionOut)
async def submit_assignment(
    assignment_id: int = Form(...),
    file: UploadFile = File(...),
    user: LMSUser = Depends(require_role("student")),
):
    @sync_to_async
    def get_assignment():
        try:
            return Assignment.objects.get(pk=assignment_id)
        except Assignment.DoesNotExist:
            raise HTTPException(status_code=404, detail="Assignment not found.")

    assignment = await get_assignment()

    @sync_to_async
    def check_enrollment():
        if not Enrollment.objects.filter(user=user, course=assignment.course).exists():
            raise HTTPException(status_code=403, detail="You are not enrolled in this course.")

    await check_enrollment()

    if timezone.now() > assignment.deadline:
        raise HTTPException(status_code=400, detail="The deadline for this assignment has passed.")

    @sync_to_async
    def save_submission():
        os.makedirs(MEDIA_ROOT, exist_ok=True)
        file_path = os.path.join(MEDIA_ROOT, f"{uuid.uuid4()}_{file.filename}")
        with open(file_path, "wb") as buffer:
            buffer.write(file.file.read())
        file_url = f"/{file_path}"
        return Submission.objects.create(
            assignment=assignment,
            student=user,
            file_url=file_url,
        )

    return await save_submission()

@router.put("/grade", response_model=SubmissionOut)
async def grade_submission(request: GradeSubmissionRequest, user: LMSUser = Depends(require_role("instructor"))):
    @sync_to_async
    def get_submission():
        try:
            return Submission.objects.select_related("assignment__course__instructor", "student").get(pk=request.submission_id)
        except Submission.DoesNotExist:
            raise HTTPException(status_code=404, detail="Submission not found.")

    submission = await get_submission()

    if submission.assignment.course.instructor != user:
        raise HTTPException(status_code=403, detail="You are not the instructor for this course.")

    @sync_to_async
    def grade_in_db():
        submission.grade = request.grade
        submission.remarks = request.remarks
        submission.save()
        return submission

    submission = await grade_in_db()
    await create_notification(submission.student, f"Your submission for '{submission.assignment.title}' has been graded.", link=f"/submissions/{submission.id}/")

    return submission

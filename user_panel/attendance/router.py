from fastapi import APIRouter, Depends, HTTPException
from typing import List
from datetime import date

from .schemas import MarkAttendanceRequest, StudentAttendanceResponse, CourseAttendanceResponse
from lms.models import Attendance, LMSUser, Course, Enrollment
from user_panel.deps import get_current_user, require_role
from asgiref.sync import sync_to_async
from user_panel.notifications.utils import create_notification

router = APIRouter(
    prefix="/attendance",
    tags=["attendance"],
)

@router.post("/mark", status_code=201)
async def mark_attendance(request: MarkAttendanceRequest, user: LMSUser = Depends(require_role("instructor"))):
    @sync_to_async
    def get_course():
        try:
            return Course.objects.get(pk=request.course_id, instructor=user)
        except Course.DoesNotExist:
            raise HTTPException(status_code=404, detail="Course not found or you are not the instructor.")

    course = await get_course()

    for record in request.records:
        @sync_to_async
        def get_student():
            try:
                return LMSUser.objects.get(pk=record.student_id, role="student")
            except LMSUser.DoesNotExist:
                raise HTTPException(status_code=404, detail=f"Student with id {record.student_id} not found.")

        student = await get_student()

        @sync_to_async
        def update_attendance():
            if not Enrollment.objects.filter(user=student, course=course).exists():
                raise HTTPException(status_code=400, detail=f"Student {student.id} is not enrolled in this course.")

            Attendance.objects.update_or_create(
                student=student,
                course=course,
                date=request.date,
                defaults={"status": record.status}
            )

        await update_attendance()
        await create_notification(student, f"Attendance marked for {course.title} on {request.date}.", link=f"/courses/{course.id}/attendance/")

    return {"message": "Attendance marked successfully."}

@router.get("/student/{student_id}", response_model=StudentAttendanceResponse)
@sync_to_async
def get_student_attendance(student_id: int, course_id: int, user: LMSUser = Depends(get_current_user)):
    records = list(Attendance.objects.filter(student_id=student_id, course_id=course_id))
    present_count = sum(1 for r in records if r.status == "Present")
    percentage = (present_count / len(records)) * 100 if records else 0
    return {"percentage": percentage, "records": records}

@router.get("/course/{course_id}", response_model=CourseAttendanceResponse)
@sync_to_async
def get_course_attendance(course_id: int, from_date: date, to_date: date, user: LMSUser = Depends(require_role("instructor"))):
    records = list(Attendance.objects.filter(course_id=course_id, date__range=[from_date, to_date]))
    present_count = sum(1 for r in records if r.status == "Present")
    percentage = (present_count / len(records)) * 100 if records else 0
    return {"percentage": percentage, "records": records}

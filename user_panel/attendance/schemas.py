from pydantic import BaseModel
from datetime import date
from typing import List

class AttendanceRecordIn(BaseModel):
    student_id: int
    status: str

class MarkAttendanceRequest(BaseModel):
    course_id: int
    date: date
    records: List[AttendanceRecordIn]

class AttendanceOut(BaseModel):
    student_id: int
    course_id: int
    date: date
    status: str

    class Config:
        orm_mode = True

class StudentAttendanceResponse(BaseModel):
    percentage: float
    records: List[AttendanceOut]

class CourseAttendanceResponse(BaseModel):
    percentage: float
    records: List[AttendanceOut]

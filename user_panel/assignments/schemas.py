from pydantic import BaseModel
from datetime import datetime

class AssignmentOut(BaseModel):
    id: int
    course_id: int
    title: str
    description: str
    deadline: datetime
    file_url: str | None

    class Config:
        orm_mode = True

class SubmissionOut(BaseModel):
    id: int
    assignment_id: int
    student_id: int
    file_url: str
    submitted_at: datetime
    grade: str | None
    remarks: str | None

    class Config:
        orm_mode = True

class GradeSubmissionRequest(BaseModel):
    submission_id: int
    grade: str
    remarks: str

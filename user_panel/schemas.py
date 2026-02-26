from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    name: str = Field(..., max_length=120)
    email: EmailStr
    password: str = Field(..., min_length=6)
    role: str = Field(..., pattern="^(student|instructor)$")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CourseOut(BaseModel):
    id: int
    title: str
    description: str
    instructor_name: str
    status: str


class EnrollRequest(BaseModel):
    course_id: int


class ProgressUpdateRequest(BaseModel):
    course_id: int
    completed_lessons: int
    progress_percent: float


class ProgressOut(BaseModel):
    course_id: int
    completed_lessons: int
    progress_percent: float


class PlanOut(BaseModel):
    id: int
    name: str
    price: float
    duration_days: int


class SubscribeRequest(BaseModel):
    plan_id: int


class PaymentOut(BaseModel):
    plan_name: str
    amount: float
    payment_date: str

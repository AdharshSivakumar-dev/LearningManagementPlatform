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


class NotificationOut(BaseModel):
    id: int
    message: str
    is_read: bool
    created_at: str


class MarkReadRequest(BaseModel):
    ids: List[int] | None = None
    mark_all: bool = False


class ActivityLogRequest(BaseModel):
    action_type: str
    action_detail: str | None = None


class AnalyticsOverviewOut(BaseModel):
    total_users: int
    active_subscriptions: int
    revenue_inr: float
    popular_course: str | None


class MonthlyRevenueOut(BaseModel):
    label: str
    value: float

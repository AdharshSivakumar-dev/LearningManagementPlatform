"""
OTP-Based Authentication Routes
==================================
Endpoints:
  POST /auth/otp/send/    - Generate and send a 6-digit OTP via email
  POST /auth/otp/verify/  - Verify OTP and issue JWT (creates account if new user)

OTP codes expire after 10 minutes and are single-use.
Delivery uses Django's configured SMTP email backend.
"""

import random
import string
import os
from datetime import timedelta

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, Field

from .django_setup import setup as django_setup
django_setup()

from django.utils import timezone  # noqa: E402
from django.core.mail import send_mail  # noqa: E402
from lms.models import LMSUser, OTPLog  # noqa: E402
from .auth import create_access_token  # noqa: E402

router = APIRouter(prefix="/auth/otp", tags=["Auth - OTP"])

OTP_EXPIRE_MINUTES = int(os.getenv("OTP_EXPIRE_MINUTES", "10"))


class OTPSendRequest(BaseModel):
    email: EmailStr
    name: str = Field(default="", description="Full name (for new user registration)")
    role: str = Field(default="student", pattern="^(student|instructor)$")


class OTPVerifyRequest(BaseModel):
    email: EmailStr
    otp_code: str = Field(..., min_length=6, max_length=6, description="6-digit OTP code")


class OTPSendResponse(BaseModel):
    message: str
    expires_in_minutes: int = OTP_EXPIRE_MINUTES


def _generate_otp() -> str:
    """Generate a cryptographically safe 6-digit numeric OTP."""
    return "".join(random.choices(string.digits, k=6))


@router.post("/send/", response_model=OTPSendResponse, summary="Send OTP to user's email")
def send_otp(payload: OTPSendRequest):
    """
    Generate a 6-digit OTP and send it to the provided email address.
    Rate limit: Only one active OTP per email is allowed — previous unused OTPs
    are invalidated before generating a new one.
    """
    # Invalidate any existing unused OTPs for this email
    OTPLog.objects.filter(email=payload.email, is_used=False).update(is_used=True)

    otp_code = _generate_otp()
    expires_at = timezone.now() + timedelta(minutes=OTP_EXPIRE_MINUTES)

    OTPLog.objects.create(
        email=payload.email,
        otp_code=otp_code,
        method="email",
        is_used=False,
        expires_at=expires_at,
    )

    # Send OTP via email
    try:
        send_mail(
            subject="Your LMS Login Code",
            message=(
                f"Your one-time login code is: {otp_code}\n\n"
                f"This code expires in {OTP_EXPIRE_MINUTES} minutes.\n"
                "If you did not request this, please ignore this email."
            ),
            from_email=None,  # Uses DEFAULT_FROM_EMAIL from settings
            recipient_list=[payload.email],
            fail_silently=False,
        )
    except Exception as exc:
        # Clean up the OTP log entry if sending fails
        OTPLog.objects.filter(email=payload.email, is_used=False).update(is_used=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send OTP email: {str(exc)}. Please check SMTP configuration.",
        )

    return OTPSendResponse(message=f"OTP sent to {payload.email}", expires_in_minutes=OTP_EXPIRE_MINUTES)


@router.post("/verify/", summary="Verify OTP and issue JWT token")
def verify_otp(payload: OTPVerifyRequest):
    """
    Validate the OTP code for the given email.
    - On success: marks OTP as used, creates user if new, returns JWT.
    - On failure: raises 401 with a descriptive error.
    """
    # Find the latest unused, non-expired OTP for this email
    try:
        otp_log = (
            OTPLog.objects.filter(
                email=payload.email,
                otp_code=payload.otp_code,
                is_used=False,
            )
            .order_by("-created_at")
            .first()
        )
    except Exception:
        raise HTTPException(status_code=500, detail="Database error while verifying OTP")

    if not otp_log:
        raise HTTPException(status_code=401, detail="Invalid OTP code")

    if not otp_log.is_valid():
        raise HTTPException(status_code=401, detail="OTP has expired or already been used")

    # Mark OTP as used
    otp_log.is_used = True
    otp_log.save(update_fields=["is_used"])

    # Find or create the LMS user
    try:
        user = LMSUser.objects.get(email=payload.email)
    except LMSUser.DoesNotExist:
        # Auto-create account for new users via OTP
        name = payload.email.split("@")[0]
        user = LMSUser.objects.create(
            name=name,
            email=payload.email,
            role="student",
            password_hash="",  # OTP-only user, no password
            is_active=True,
        )

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Your account has been deactivated")

    jwt = create_access_token(str(user.id), user.role)

    return {
        "access_token": jwt,
        "token_type": "bearer",
        "user_id": user.id,
        "username": user.name,
        "message": "OTP verified successfully",
    }

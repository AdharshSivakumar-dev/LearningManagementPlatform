"""
Google OAuth2 Authentication Routes
====================================
Endpoints:
  GET /auth/google/           - Redirect user to Google OAuth2 consent page
  GET /auth/google/callback/  - Handle Google OAuth2 callback, issue JWT

Required .env variables:
  GOOGLE_CLIENT_ID
  GOOGLE_CLIENT_SECRET
  OAUTH_REDIRECT_BASE   (e.g. http://localhost:8001)
"""

import os
import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

from .django_setup import setup as django_setup
django_setup()

from lms.models import LMSUser, SocialAccount  # noqa: E402
from .auth import create_access_token  # noqa: E402

router = APIRouter(prefix="/auth/google", tags=["Auth - Google"])

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
OAUTH_REDIRECT_BASE = os.getenv("OAUTH_REDIRECT_BASE", "http://localhost:8001")
GOOGLE_REDIRECT_URI = f"{OAUTH_REDIRECT_BASE}/auth/google/callback/"
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
GOOGLE_SCOPES = "openid email profile"


@router.get("/", summary="Redirect to Google OAuth2 consent page")
def google_login():
    """Initiate Google OAuth2 login flow."""
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=501,
            detail="Google OAuth is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env",
        )
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": GOOGLE_SCOPES,
        "access_type": "offline",
        "prompt": "select_account",
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(url=f"{GOOGLE_AUTH_URL}?{query}")


@router.get("/callback/", summary="Google OAuth2 callback handler")
def google_callback(code: str = "", error: str = ""):
    """Handle Google OAuth2 redirect, exchange code for user info, issue JWT."""
    if error or not code:
        raise HTTPException(status_code=400, detail=f"Google OAuth error: {error or 'No code returned'}")

    # Exchange code for tokens
    token_resp = httpx.post(
        GOOGLE_TOKEN_URL,
        data={
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        },
        timeout=15,
    )
    if token_resp.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to exchange Google auth code for token")

    token_data = token_resp.json()
    access_token = token_data.get("access_token", "")

    # Fetch user info
    user_resp = httpx.get(
        GOOGLE_USERINFO_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    if user_resp.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to fetch Google user info")

    info = user_resp.json()
    provider_id = str(info.get("id", ""))
    email = info.get("email", "")
    name = info.get("name", email.split("@")[0])

    if not email:
        raise HTTPException(status_code=400, detail="Google account did not return an email address")

    # Find or create LMSUser
    try:
        user = LMSUser.objects.get(email=email)
    except LMSUser.DoesNotExist:
        user = LMSUser.objects.create(
            name=name,
            email=email,
            role="student",
            password_hash="",  # Social login — no password
            is_active=True,
        )

    # Upsert SocialAccount
    SocialAccount.objects.update_or_create(
        provider="google",
        provider_user_id=provider_id,
        defaults={"user": user, "provider_email": email, "access_token": access_token},
    )

    jwt = create_access_token(str(user.id), user.role)

    # Redirect to login page with token in query param (UI will pick it up)
    redirect_url = f"{OAUTH_REDIRECT_BASE}/login/?token={jwt}&user_id={user.id}&username={user.name}"
    return RedirectResponse(url=redirect_url)

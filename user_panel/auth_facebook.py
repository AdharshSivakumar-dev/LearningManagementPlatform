"""
Facebook OAuth2 Authentication Routes
=======================================
Endpoints:
  GET /auth/facebook/           - Redirect user to Facebook OAuth2 dialog
  GET /auth/facebook/callback/  - Handle Facebook OAuth2 callback, issue JWT

Required .env variables:
  FACEBOOK_CLIENT_ID     (App ID)
  FACEBOOK_CLIENT_SECRET (App Secret)
  OAUTH_REDIRECT_BASE    (e.g. http://localhost:8001)
"""

import os
import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

from .django_setup import setup as django_setup
django_setup()

from lms.models import LMSUser, SocialAccount  # noqa: E402
from .auth import create_access_token  # noqa: E402

router = APIRouter(prefix="/auth/facebook", tags=["Auth - Facebook"])

FACEBOOK_CLIENT_ID = os.getenv("FACEBOOK_CLIENT_ID", "")
FACEBOOK_CLIENT_SECRET = os.getenv("FACEBOOK_CLIENT_SECRET", "")
OAUTH_REDIRECT_BASE = os.getenv("OAUTH_REDIRECT_BASE", "http://localhost:8001")
FACEBOOK_REDIRECT_URI = f"{OAUTH_REDIRECT_BASE}/auth/facebook/callback/"
FACEBOOK_AUTH_URL = "https://www.facebook.com/v19.0/dialog/oauth"
FACEBOOK_TOKEN_URL = "https://graph.facebook.com/v19.0/oauth/access_token"
FACEBOOK_USERINFO_URL = "https://graph.facebook.com/me"


@router.get("/", summary="Redirect to Facebook OAuth2 dialog")
def facebook_login():
    """Initiate Facebook OAuth2 login flow."""
    if not FACEBOOK_CLIENT_ID:
        raise HTTPException(
            status_code=501,
            detail="Facebook OAuth is not configured. Set FACEBOOK_CLIENT_ID and FACEBOOK_CLIENT_SECRET in .env",
        )
    params = {
        "client_id": FACEBOOK_CLIENT_ID,
        "redirect_uri": FACEBOOK_REDIRECT_URI,
        "scope": "email,public_profile",
        "response_type": "code",
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(url=f"{FACEBOOK_AUTH_URL}?{query}")


@router.get("/callback/", summary="Facebook OAuth2 callback handler")
def facebook_callback(code: str = "", error: str = ""):
    """Handle Facebook callback, exchange code for user info, issue JWT."""
    if error or not code:
        raise HTTPException(status_code=400, detail=f"Facebook OAuth error: {error or 'No code returned'}")

    # Exchange code for access token
    token_resp = httpx.get(
        FACEBOOK_TOKEN_URL,
        params={
            "client_id": FACEBOOK_CLIENT_ID,
            "client_secret": FACEBOOK_CLIENT_SECRET,
            "redirect_uri": FACEBOOK_REDIRECT_URI,
            "code": code,
        },
        timeout=15,
    )
    if token_resp.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to exchange Facebook auth code for token")

    access_token = token_resp.json().get("access_token", "")

    # Fetch user info (id, name, email)
    user_resp = httpx.get(
        FACEBOOK_USERINFO_URL,
        params={"fields": "id,name,email", "access_token": access_token},
        timeout=10,
    )
    if user_resp.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to fetch Facebook user info")

    info = user_resp.json()
    provider_id = str(info.get("id", ""))
    email = info.get("email", "")
    name = info.get("name", "Facebook User")

    if not email:
        # Facebook may not expose email depending on app permissions
        raise HTTPException(
            status_code=400,
            detail="Facebook account did not return an email. Ensure your app has 'email' permission.",
        )

    # Find or create LMSUser
    try:
        user = LMSUser.objects.get(email=email)
    except LMSUser.DoesNotExist:
        user = LMSUser.objects.create(
            name=name,
            email=email,
            role="student",
            password_hash="",
            is_active=True,
        )

    # Upsert SocialAccount
    SocialAccount.objects.update_or_create(
        provider="facebook",
        provider_user_id=provider_id,
        defaults={"user": user, "provider_email": email, "access_token": access_token},
    )

    jwt = create_access_token(str(user.id), user.role)
    return RedirectResponse(url=f"{OAUTH_REDIRECT_BASE}/login/?token={jwt}&user_id={user.id}&username={user.name}")

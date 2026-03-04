"""
GitHub OAuth2 Authentication Routes
=====================================
Endpoints:
  GET /auth/github/           - Redirect user to GitHub OAuth2 authorization page
  GET /auth/github/callback/  - Handle GitHub OAuth2 callback, issue JWT

Required .env variables:
  GITHUB_CLIENT_ID
  GITHUB_CLIENT_SECRET
  OAUTH_REDIRECT_BASE   (e.g. http://localhost:8000)
"""

import os
import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

from .django_setup import setup as django_setup
django_setup()

from lms.models import LMSUser, SocialAccount  # noqa: E402
from .auth import create_access_token  # noqa: E402

router = APIRouter(prefix="/auth/github", tags=["Auth - GitHub"])

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "")
OAUTH_REDIRECT_BASE = os.getenv("OAUTH_REDIRECT_BASE", "http://localhost:8001")
GITHUB_REDIRECT_URI = f"{OAUTH_REDIRECT_BASE}/auth/github/callback/"
GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USERINFO_URL = "https://api.github.com/user"
GITHUB_EMAIL_URL = "https://api.github.com/user/emails"


@router.get("/", summary="Redirect to GitHub OAuth2 authorization page")
def github_login():
    """Initiate GitHub OAuth2 login flow."""
    if not GITHUB_CLIENT_ID:
        raise HTTPException(
            status_code=501,
            detail="GitHub OAuth is not configured. Set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET in .env",
        )
    params = {
        "client_id": GITHUB_CLIENT_ID,
        "redirect_uri": GITHUB_REDIRECT_URI,
        "scope": "read:user user:email",
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(url=f"{GITHUB_AUTH_URL}?{query}")


@router.get("/callback/", summary="GitHub OAuth2 callback handler")
def github_callback(code: str = "", error: str = ""):
    """Handle GitHub OAuth2 redirect, exchange code for token, issue JWT."""
    if error or not code:
        raise HTTPException(status_code=400, detail=f"GitHub OAuth error: {error or 'No code returned'}")

    # Exchange code for access token
    token_resp = httpx.post(
        GITHUB_TOKEN_URL,
        json={
            "client_id": GITHUB_CLIENT_ID,
            "client_secret": GITHUB_CLIENT_SECRET,
            "code": code,
            "redirect_uri": GITHUB_REDIRECT_URI,
        },
        headers={"Accept": "application/json"},
        timeout=15,
    )
    if token_resp.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to exchange GitHub auth code for token")

    access_token = token_resp.json().get("access_token", "")
    auth_headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}

    # Fetch user info
    user_resp = httpx.get(GITHUB_USERINFO_URL, headers=auth_headers, timeout=10)
    if user_resp.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to fetch GitHub user info")

    info = user_resp.json()
    provider_id = str(info.get("id", ""))
    name = info.get("name") or info.get("login", "GitHub User")
    email = info.get("email", "")

    # GitHub may not expose email in profile; fetch from emails endpoint
    if not email:
        emails_resp = httpx.get(GITHUB_EMAIL_URL, headers=auth_headers, timeout=10)
        if emails_resp.status_code == 200:
            emails = emails_resp.json()
            # Prefer primary + verified email
            for e in emails:
                if e.get("primary") and e.get("verified"):
                    email = e.get("email", "")
                    break
            if not email and emails:
                email = emails[0].get("email", "")

    if not email:
        raise HTTPException(
            status_code=400,
            detail="GitHub account does not have a public email. Please set a public email in GitHub settings.",
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
        provider="github",
        provider_user_id=provider_id,
        defaults={"user": user, "provider_email": email, "access_token": access_token},
    )

    jwt = create_access_token(str(user.id), user.role)
    return RedirectResponse(url=f"{OAUTH_REDIRECT_BASE}/login/?token={jwt}&user_id={user.id}&username={user.name}")

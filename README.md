# Learning Management Platform

A comprehensive LMS platform featuring a Django-based Admin Panel and a FastAPI-powered User Panel. This project includes course management, subscriptions, real-time chat, advanced academic modules, and a complete authentication system with social logins and OTP.

## Authentication Features

- **Email/Password Login & Registration** — JWT-based via FastAPI
- **Social Login** — Google, Facebook, GitHub OAuth2 redirect flows
- **OTP Login/Signup** — 6-digit code delivered via email, expires in 10 minutes
- **Unified Login/Signup Page** — accessible at `http://localhost:8000/login/`
- **JWT Tokens** — issued on all successful auth flows

## Recent Updates

- **Auth System:** Unified login/signup page with social OAuth2 and OTP authentication
- **Social Accounts Model:** Django model tracking linked provider accounts per user
- **OTP Log Model:** Django model tracking OTP sends, usage, and expiry per email
- **Attendance Tracking:** Fully integrated system to mark student attendance per course
- **Assignment Management:** Robust module for instructors to create and grade assignments
- **Course Analytics:** Server-side aggregation endpoints for course performance
- **Automated Notifications:** Event-driven in-app and email alerts

## Tech Stack

- **Backend:** Python 3.11+, Django 5.x, FastAPI, Uvicorn
- **Auth:** JWT (python-jose), bcrypt (passlib), OAuth2 (httpx), email OTP
- **Database:** SQLite (Development) / PostgreSQL (Production)
- **Real-time:** WebSockets (FastAPI), Redis (Pub/Sub)
- **Email:** SMTP Integration (OTP delivery + enrollment notifications)

## Setup and Installation

### 1. Environment Setup

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .\.venv\Scripts\Activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

Key variables to set:
| Variable | Description |
|---|---|
| `DJANGO_SECRET_KEY` | Django secret key |
| `JWT_SECRET` | JWT signing secret |
| `EMAIL_HOST_USER` | Gmail address for OTP delivery |
| `EMAIL_HOST_PASSWORD` | Gmail App Password |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Google OAuth2 credentials |
| `FACEBOOK_CLIENT_ID` / `FACEBOOK_CLIENT_SECRET` | Facebook App credentials |
| `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` | GitHub OAuth App credentials |
| `OAUTH_REDIRECT_BASE` | FastAPI base URL (default: `http://localhost:8000`) |

### 3. Database Initialization

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

### 4. Running the Platform

Start Redis server (required for real-time chat):
```bash
redis-server
```

Start Django (Admin + Dashboard + Login page):
```bash
python manage.py runserver
```

Start FastAPI (User Panel + Auth API):
```bash
uvicorn user_panel.main:app --port 8001 --reload
```

## OAuth2 Provider Setup

### Google
1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create OAuth 2.0 Client ID (Web application)
3. Add Authorized redirect URI: `http://localhost:8000/auth/google/callback/`
4. Copy Client ID and Client Secret to `.env`

### Facebook
1. Go to [Facebook Developers](https://developers.facebook.com/apps/)
2. Create an App → Add Facebook Login product
3. Add Valid OAuth Redirect URI: `http://localhost:8000/auth/facebook/callback/`
4. Copy App ID and App Secret to `.env`

### GitHub
1. Go to [GitHub Developer Settings](https://github.com/settings/developers)
2. Create a new OAuth App
3. Set Authorization callback URL: `http://localhost:8000/auth/github/callback/`
4. Copy Client ID and Client Secret to `.env`

## API Documentation

| URL | Description |
|---|---|
| `http://localhost:8000/login/` | Unified Login / Sign-Up Page |
| `http://localhost:8001/docs` | Interactive Swagger UI (all API endpoints) |
| `http://localhost:8000/admin/` | Django Admin Panel |
| `http://localhost:8000/admin/dashboard/` | LMS Analytics Dashboard |
| `http://localhost:8000/admin/chat/` | Real-time Chat |

## Key API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/register/` | Register with email + password |
| `POST` | `/login/` | Login with email + password |
| `POST` | `/token/` | OAuth2 password flow (Swagger UI) |
| `GET` | `/auth/google/` | Start Google OAuth2 flow |
| `GET` | `/auth/facebook/` | Start Facebook OAuth2 flow |
| `GET` | `/auth/github/` | Start GitHub OAuth2 flow |
| `POST` | `/auth/otp/send/` | Send OTP to email |
| `POST` | `/auth/otp/verify/` | Verify OTP and get JWT |

## License

This project is licensed under the MIT License.

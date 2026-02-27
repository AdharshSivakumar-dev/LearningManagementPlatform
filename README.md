Learning Management Platform (Django Admin + FastAPI User Panel)

Setup Guide
- Prerequisites: Python 3.11+, pip, Git
- Copy environment: cp .env.example .env and fill secrets (JWT, SMTP, optional DB URL)
- Install dependencies:
  - python -m venv .venv
  - .\.venv\Scripts\Activate.ps1
  - pip install -r requirements.txt
- Initialize database:
  - python manage.py migrate
  - python manage.py createsuperuser
- Run services:
  - Admin: python manage.py runserver 0.0.0.0:8000
  - API: uvicorn user_panel.main:app --host 0.0.0.0 --port 8001

Email Setup (Gmail SMTP)
- Enable 2‑Step Verification in Google Account
- Create an App Password for “Mail” and copy it
- Edit .env:
  - EMAIL_HOST_USER=your_gmail_address@gmail.com
  - EMAIL_HOST_PASSWORD=<your_app_password>
- Restart Admin and API servers

Testing Guide
- Auth:
  - POST /auth/register/ → create user; POST /token/ → get JWT (username=email)
  - Use Authorize in Swagger (http://localhost:8001/docs)
- Plans & Subscriptions:
  - Add plans in Admin; GET /plans/ then POST /subscribe/ to purchase
  - Expect: email to user; in‑app notification; Payment recorded
- Courses & Enrollments:
  - Publish courses; POST /enroll/ to enroll
  - Expect: emails to student and instructor; in‑app notifications; activity log
- Notifications & Activity:
  - GET /notifications/ (user) → verify notifications
  - Dashboard charts: revenue after subscribe; activity after subscribe/enroll/view

GitHub Push
- Ensure .env is ignored (.gitignore already includes it)
- git init
- git checkout -b main
- git add .
- git commit -m "Finalize LMS with subscriptions, analytics, notifications, SMTP email"
- git remote add origin <your_repo_url>
- git push -u origin main

Overview
- Django powers the Admin Panel (CRUD, dashboard, reports).
- FastAPI powers the User Panel backend (JWT auth, course browsing, enrollments, progress, subscriptions).
- Both share one database (PostgreSQL via DATABASE_URL). SQLite is supported for quick local dev.

Tech Stack
- Django 4.2, FastAPI, Uvicorn
- PostgreSQL (Dockerized), Chart.js, Bootstrap 5 (Material 3-inspired pastels)

Project Layout
- manage.py — Django entry point
- lms_admin/ — Django project (settings/urls)
- lms/ — LMS app (models, admin, dashboard, migrations)
- user_panel/ — FastAPI app (main, auth, schemas)
- docker-compose.yml — db + services
- postman_collection.json — API requests

Quick Start (Docker) (Local Run)
1) Copy .env.example to .env and adjust secrets if needed.
2) Run: docker compose up --build
3) Django Admin: http://localhost:8000/admin/ (create a superuser in the container if needed)
4) Custom Admin Dashboard: http://localhost:8000/admin/dashboard/
5) FastAPI: http://localhost:8001/docs (interactive Swagger)

Local Dev (without Docker)
1) Python 3.11 and pip installed.
2) Create venv and install deps:
   - python -m venv .venv
   - .venv\\Scripts\\activate (Windows) or source .venv/bin/activate (Unix)
   - pip install -r requirements.txt
3) Configure DB:
   - Default uses SQLite. To use Postgres set DATABASE_URL in environment.
4) Initialize DB schema (Django migrations):
   - python manage.py migrate
   - python manage.py createsuperuser
5) Run Django Admin:
   - python manage.py runserver 8000
6) Run FastAPI User Panel:
   - uvicorn user_panel.main:app --reload --port 8001

Admin Features (Django)
- Admin login/logout via Django Auth
- Dashboard with totals and “Top Enrolled Courses” chart (Chart.js)
- Analytics: Monthly revenue (INR) and Activity trend line charts
- Manage Users (approve/deactivate), Courses (inline lessons, pricing, commissions), Enrollments, Progress
- Manage Plans, Subscriptions, and Payments (INR pricing)

User Panel (FastAPI)
Auth
- POST /token/ — OAuth2 password flow (username=email) returns JWT
- POST /auth/register/ — create user and return JWT
- POST /auth/login/ — login returning JWT
Plans
- GET /plans/ — list plans (INR)
- POST /subscribe/ — purchase plan (creates Subscription + Payment)
Courses
- GET /courses/ — free courses for non-subscribers; all courses with valid subscription
- GET /courses/{id} — guards premium content behind valid subscription
Enrollments
- POST /enroll/ — enroll as student
- GET /my-courses/ — your enrolled list
Progress
- POST /progress/update/ — update progress
- GET /progress/view/ — view progress
Notifications & Activity
- GET /notifications/ — list notifications
- POST /notifications/mark-read/ — mark selected/all as read
- POST /activity/ — log user actions
Analytics (Instructor)
- GET /analytics/overview/ — totals, active subs, revenue, popular course
- GET /analytics/monthly/ — monthly revenue series (INR)
Instructor
- POST /courses/create/ — create a course (role=instructor)

Models
- LMSUser(id, name, email, role[student/instructor], password_hash, is_active)
- Course(id, title, description, instructor_id, status[draft/published/archived], is_premium, price[INR], instructor_commission_percent)
- Lesson(id, course_id, title, content, video_url, order)
- Enrollment(id, user_id, course_id, enrolled_on unique(user,course))
- Progress(id, enrollment_id one-to-one, completed_lessons, progress_percent)
- Plan(id, name, price[INR], duration_days)
- Subscription(id, user_id, plan_id, start_date, end_date, status)
- Payment(id, user_id, plan_id, amount[INR], payment_date)
- Notification(id, user_id, message, is_read, created_at)
- ActivityLog(id, user_id, action_type, action_detail, created_at)
- AnalyticsRecord(date, total_users, active_subscriptions, revenue, popular_course)

Postman
- Import postman_collection.json
- Use Register → Login to obtain token; set variable {{token}}

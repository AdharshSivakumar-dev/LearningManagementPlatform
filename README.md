Learning Management Platform (Django Admin + FastAPI User Panel)

Overview
- Django powers the Admin Panel (CRUD, dashboard, reports).
- FastAPI powers the User Panel backend (JWT auth, course browsing, enrollments, progress).
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
- Manage Users, Courses (inline lessons), Enrollments, Progress

User Panel (FastAPI)
Auth
- POST /register/ — create user and return JWT
- POST /login/ — login returning JWT
Courses
- GET /courses/ — list published courses
- GET /courses/{id} — get course details
Enrollments
- POST /enroll/ — enroll as student
- GET /my-courses/ — your enrolled list
Progress
- POST /progress/update/ — update progress
- GET /progress/view/ — view progress
Instructor
- POST /courses/create/ — create a course (role=instructor)

Models
- LMSUser(id, name, email, role[student/instructor], password_hash)
- Course(id, title, description, instructor_id, status[draft/published/archived])
- Lesson(id, course_id, title, content, video_url, order)
- Enrollment(id, user_id, course_id, enrolled_on unique(user,course))
- Progress(id, enrollment_id one-to-one, completed_lessons, progress_percent)

Postman
- Import postman_collection.json
- Use Register → Login to obtain token; set variable {{token}}


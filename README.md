# Learning Management Platform

A comprehensive LMS platform featuring a Django-based Admin Panel and a FastAPI-powered User Panel. This project includes course management, subscriptions, real-time chat, and advanced academic modules.

## Recent Updates

The following features were implemented to enhance student tracking and academic management:

- **Attendance Tracking:** Fully integrated system to mark student attendance per course. Students and instructors can view attendance records, with automatic percentage calculations for performance monitoring.
- **Assignment Management:** Robust module for instructors to create assignments with deadlines. Students can submit their work via file uploads, and instructors can provide grades and feedback directly through the API.
- **Course Analytics:** Server-side aggregation endpoints providing JSON data for course performance, including student enrollment counts, average attendance rates, and submission statistics.
- **Automated Notifications:** Event-driven notification system that triggers both in-app and email alerts when assignments are created, graded, or when attendance is marked.

## Tech Stack

- **Backend:** Python 3.11+, Django 4.2, FastAPI, Uvicorn
- **Database:** SQLite (Development)
- **Real-time:** WebSockets (FastAPI), Redis (Pub/Sub)
- **Email:** SMTP Integration for automated alerts

## Setup and Installation

1.  **Environment Setup:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # .\ .venv\Scripts\Activate on Windows
    pip install -r requirements.txt
    ```

2.  **Database Initialization:**
    ```bash
    python manage.py migrate
    python manage.py createsuperuser
    ```

3.  **Running the Platform:**
    - Start Redis server
    - Django (Admin/Analytics): `python manage.py runserver`
    - FastAPI (User Panel/API): `uvicorn user_panel.main:app --port 8001`

## API Documentation

- **Interactive Swagger UI:** `http://localhost:8001/docs`
- **Django Admin Panel:** `http://localhost:8000/admin/`
- **Course Analytics Endpoint:** `http://localhost:8000/analytics/dashboard/?course_id={id}`

## License

This project is licensed under the MIT License.

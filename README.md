# Learning Management Platform

A comprehensive LMS platform featuring a Django-based Admin Panel and a FastAPI-powered User Panel. This project includes course management, subscriptions, real-time chat, and analytics.

## Features

- **Admin Panel (Django):**
  - Course & Lesson Management
  - User Management (Instructors & Students)
  - Dashboard with Revenue & Enrollment Analytics
  - Real-time Chat Analytics
  - Notification Management

- **User Panel (FastAPI):**
  - JWT Authentication (Register/Login)
  - Course Browsing & Enrollment
  - Progress Tracking
  - Real-time Chat (Private & Group) with WebSocket
  - File Sharing in Chat
  - Real-time Notifications

## Tech Stack

- **Backend:** Python 3.11+, Django 4.2, FastAPI, Uvicorn
- **Database:** PostgreSQL (production) or SQLite (dev)
- **Real-time:** WebSockets (FastAPI), Redis (Pub/Sub)
- **Frontend:** Django Templates, Bootstrap 5, Chart.js

## Setup Guide

### Prerequisites
- Python 3.11+
- Redis (for real-time features)

### Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd LearningManagementPlatform
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv .venv
    # Windows
    .\.venv\Scripts\Activate
    # Linux/Mac
    source .venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment:**
    Copy `.env.example` to `.env` and update the values:
    ```bash
    cp .env.example .env
    ```
    Ensure `REDIS_URL` is set correctly (e.g., `redis://localhost:6379`).

5.  **Initialize Database:**
    ```bash
    python manage.py migrate
    python manage.py createsuperuser
    ```

### Running the Application

You need to run both the Django server (Frontend/Admin) and the FastAPI server (API/WebSockets).

1.  **Start Redis Server:**
    ```bash
    redis-server
    ```

2.  **Start Django Server (Terminal 1):**
    ```bash
    python manage.py runserver 0.0.0.0:8000
    ```

3.  **Start FastAPI Server (Terminal 2):**
    ```bash
    uvicorn user_panel.main:app --host 0.0.0.0 --port 8001
    ```

### Accessing the App

- **Admin Dashboard:** [http://localhost:8000/admin/dashboard/](http://localhost:8000/admin/dashboard/)
- **Chat Interface:** [http://localhost:8000/admin/chat/](http://localhost:8000/admin/chat/)
- **API Documentation:** [http://localhost:8001/docs](http://localhost:8001/docs)

## Project Structure

- `lms/`: Django app for Admin, Models, and Templates.
- `user_panel/`: FastAPI app for API endpoints and WebSockets.
- `lms_admin/`: Django project settings.
- `requirements.txt`: Python dependencies.

## Key Functionalities

- **Chat:** Users can create private or group rooms, exchange messages, and share files. Real-time updates are handled via WebSockets and Redis.
- **Analytics:** Admins can view chat activity, active rooms, and file sharing statistics.
- **Notifications:** Users receive real-time notifications for new messages.

## License

This project is open-source and available under the MIT License.

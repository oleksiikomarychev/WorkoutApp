# WorkoutApp Backend

This project contains the FastAPI backend for the WorkoutApp.

## Features

- User Management (Athletes, Trainers)
- Exercise Library and Tracking
- Progression Templates
- Workout Creation and Logging
- Strength Testing
- Performance Analytics

## Project Structure

- `app/`: Main application code
  - `models/`: SQLAlchemy database models
  - `schemas/`: Pydantic data validation schemas
  - `repositories/`: Data access layer
  - `services/`: Business logic layer
  - `routers/`: API endpoint definitions
  - `database.py`: Database connection and session management
  - `main.py`: FastAPI application entry point
- `requirements.txt`: Python dependencies
- `alembic/`: (Optional) Alembic migration scripts directory
- `alembic.ini`: (Optional) Alembic configuration

## Setup and Running

1.  **Create a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Set up environment variables:**
    Create a `.env` file in the root directory and add your `DATABASE_URL`:
    ```env
    DATABASE_URL="postgresql://youruser:yourpassword@yourhost:yourport/yourdatabase"
    ```
    Example for a local PostgreSQL database named `workoutapp_db` with user `workoutuser` and password `workoutpass`:
    ```env
    DATABASE_URL="postgresql://workoutuser:workoutpass@localhost:5432/workoutapp_db"
    ```

4.  **Database Migrations (if using Alembic):**
    If you have Alembic set up (recommended for production and evolving schemas):
    ```bash
    # Initialize Alembic (only once per project)
    # alembic init alembic
    
    # Edit alembic.ini to point to your database URL (if not using env var directly in env.py)
    # Edit alembic/env.py to import your Base from app.database and set target_metadata = Base.metadata
    
    # Create a new migration script after model changes
    # alembic revision -m "create_user_tables"
    
    # Apply migrations
    # alembic upgrade head
    ```
    If you are not using Alembic for now, the `Base.metadata.create_all(bind=engine)` line in `app/main.py` will create tables based on your models when the application starts. This is suitable for early development.

5.  **Run the application:**
    ```bash
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    ```

Access the API documentation at [http://localhost:8000/docs](http://localhost:8000/docs).


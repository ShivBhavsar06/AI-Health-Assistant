# HealthMate AI

Full-stack web application for personal health, medicines, appointments, reports, feedback, and the HealthMate AI assistant.

## Stack

- Frontend: HTML5, CSS3, Bootstrap 5, vanilla JavaScript, Jinja templates
- Backend: Python, Flask
- Database: MySQL
- AI: OpenRouter API through the OpenAI-compatible Python SDK (server-side only)

This project uses Flask only.

## Project structure

The application code is organized under the `app/` package:

```
app/
├── __init__.py                 # Flask application factory
├── config.py                   # Environment and test configuration
├── extensions.py               # SQLAlchemy and CSRF extensions
├── database.py                 # Table setup and legacy migrations
├── cli.py                      # Flask CLI commands
├── models/                     # SQLAlchemy model interfaces
├── routes/                     # Blueprint interfaces
├── services/                   # AI, reminders, and email services
├── utils/                      # Auth, validation, files, OTP, and helpers
├── templates/                  # Jinja templates
└── static/                     # CSS, JavaScript, and images
```

The root-level `models/`, `routes/`, and `utils/` packages remain as compatibility
modules for existing integrations and tests. New code should import through `app`.
Runtime data in `uploads/` is intentionally kept outside the application package.

## Primary keys

Every business table uses a `VARCHAR(20)` primary key generated in Python (`utils/id_generator.py`). Foreign keys are also `VARCHAR(20)`. There is no `AUTO_INCREMENT` on these IDs.

Prefixes: `USR`, `ADM`, `MED`, `REM`, `APP`, `HRC`, `REP`, `FDB`.

The live MySQL schema uses `VARCHAR(20)` primary keys and foreign keys for all
business records. `users.email` and `admins.email` are unique; each health record
has one unique `user_id`; child records reference `users.user_id` with cascade
delete; reminders reference either a medicine or appointment. The application
factory applies a one-time compatibility migration for older databases whose
child IDs were still numeric, preserving the existing table and column names.

## Setup

1. Create a MySQL database named in `.env` (`ai_health_management` by default in the included local config).
2. Copy `.env.example` to `.env` and fill in secrets. Never commit `.env`.
3. Create a virtual environment and install dependencies:

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

4. Ensure the database tables exist:

```
python -c "from run import app"
```

5. Create an administrator:

```
set FLASK_APP=run.py
flask create-admin
```

If this database was created before the current email constraint was applied, inspect
the existing indexes before changing them. The current schema requires unique patient
emails.

```
flask allow-duplicate-user-emails
```

That legacy command is retained for installations that intentionally choose to remove
the old unique email index; it is not required for the current schema.

6. Run the server:

```
python run.py
```

- User site: `http://127.0.0.1:5000/`
- Administrator login: `http://127.0.0.1:5000/admin/login`

## Email and OTP

OTP is used only for password recovery. If SMTP settings are empty, OTP messages are
printed in development. OTP values are stored as hashed codes in the Flask session,
not in the `users` table.

## OpenRouter

Set `OPENROUTER_API_KEY` in `.env`. The default model is `openai/gpt-4o-mini`; change it with `OPENROUTER_MODEL` to any model available in your OpenRouter account. The browser never receives the key. If the API is unavailable, the assistant shows a friendly message and the site does not crash. Conversations are handled privately for the current session.


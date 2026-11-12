# HealthMate AI

HealthMate AI is a Flask web application for managing personal health information. It combines patient-facing tools for health records, medicines, appointments, reminders, medical reports, and feedback with an administrator area and an optional AI health assistant.

> **Medical disclaimer:** HealthMate AI is an information and record-keeping tool. AI responses are not a diagnosis, treatment plan, or substitute for advice from a qualified healthcare professional. Seek professional care for medical decisions or urgent symptoms.

## Contents

- [Features](#features)
- [Technology](#technology)
- [Application structure](#application-structure)
- [Requirements](#requirements)
- [Configuration](#configuration)
- [Installation and setup](#installation-and-setup)
- [Run the application](#run-the-application)
- [CLI commands](#cli-commands)
- [Data model and database](#data-model-and-database)
- [Uploads and privacy](#uploads-and-privacy)
- [AI assistant](#ai-assistant)
- [Email and password recovery](#email-and-password-recovery)
- [Development notes](#development-notes)
- [Troubleshooting](#troubleshooting)

## Features

### Patient experience

- Account registration, login, logout, profile management, and account deletion.
- Dashboard with access to personal health information and activity views.
- Health record creation and updates, including lifestyle information.
- Medicine list and detail pages, with add, edit, and delete actions.
- Appointment management and reminders, including marking reminders complete.
- Medical report upload, search, detail, edit, download, and deletion.
- Feedback submission and management.
- Optional AI assistant for health-related questions, recommendations, and report summaries. AI responses can be exported as PDF, Excel, or PNG.
- Password recovery using a one-time code (OTP).

### Administrator experience

Administrators can manage users, medicines, appointments, health records, and reports, review feedback, and access an administrative dashboard and settings. Admin accounts are provisioned through the Flask CLI rather than public registration.

## Technology

- **Backend:** Python 3, Flask 3, Flask-SQLAlchemy, SQLAlchemy
- **Database:** MySQL through PyMySQL
- **Forms and request protection:** Flask-WTF and CSRF protection
- **UI:** Jinja templates, HTML, CSS, Bootstrap-based components, and vanilla JavaScript
- **AI integration:** OpenRouter's OpenAI-compatible API via the OpenAI Python SDK
- **Documents and media:** Pillow, ReportLab, openpyxl, pypdf, and python-docx
- **Configuration:** environment variables loaded from `.env` with python-dotenv

## Application structure

```text
.
├── app/                   # Flask application package
│   ├── __init__.py        # Application factory, handlers, protected upload route
│   ├── config.py          # Configuration interface
│   ├── models/            # Application model interfaces
│   ├── routes/            # Blueprint registration interface
│   ├── services/          # Service interfaces
│   ├── static/            # CSS, JavaScript, and static assets
│   ├── templates/         # Jinja templates
│   └── utils/             # Utility interfaces
├── models/                # SQLAlchemy models
├── routes/                # Blueprint route implementations
├── utils/                 # Auth, AI, file, OTP, email, and helper implementations
├── uploads/               # Runtime user uploads (not source-controlled)
├── database.py            # Table creation and compatibility migrations
├── extensions.py          # Shared SQLAlchemy and CSRF extensions
├── flask_config.py        # Environment-backed Flask configuration
├── cli.py                 # Administrative Flask CLI commands
├── run.py                 # Application entry point
├── requirements.txt       # Python dependencies
└── .env.example           # Environment variable template
```

The project currently keeps the substantive route, model, service, and utility implementations in the root-level `routes/`, `models/`, and `utils/` packages. The matching modules under `app/` provide application-package interfaces and import registration. `run.py` creates the Flask app through `app.create_app()`.

## Requirements

- Python 3.10 or newer
- MySQL 8.0 or a compatible MySQL server
- pip
- OpenRouter API credentials for AI features (optional)
- SMTP credentials for email-based OTP delivery (optional for local development)

## Configuration

1. Copy `.env.example` to `.env`.
2. Set a unique `SECRET_KEY`, database credentials, and any optional integration settings.
3. Keep `.env` private. It contains secrets and is excluded from version control.

| Variable | Purpose | Default / notes |
| --- | --- | --- |
| `SECRET_KEY` | Signs Flask sessions | Replace with a long, random secret before deployment. |
| `DEBUG` | Enables Flask debug behavior | `True` in the current configuration when unset; set `False` for production. |
| `DB_HOST` | MySQL host | `localhost` |
| `DB_PORT` | MySQL port | `3306` |
| `DB_NAME` | Database name | `ai_health_management` |
| `DB_USER` | Database user | `root` |
| `DB_PASSWORD` | Database password | Set locally; do not use a sample or shared password. |
| `SESSION_COOKIE_SECURE` | Send session cookie only over HTTPS | Defaults to enabled when `DEBUG=False`; use HTTPS in production. |
| `REMEMBER_ME_DAYS` | Session lifetime in days | `30` |
| `OPENROUTER_API_KEY` | Enables AI requests | Optional; the browser does not receive this key. |
| `OPENROUTER_MODEL` | OpenRouter model identifier | `openai/gpt-4o-mini` |
| `OPENROUTER_BASE_URL` | OpenRouter API base URL | `https://openrouter.ai/api/v1` |
| `OPENROUTER_SITE_URL` | Optional site URL sent with provider requests | Set to the deployed site URL when applicable. |
| `OPENROUTER_APP_NAME` | Optional application name sent with provider requests | `HealthMate AI` |
| `MAIL_SERVER` / `EMAIL_HOST` | SMTP host | Either naming convention is supported. |
| `MAIL_PORT` / `EMAIL_PORT` | SMTP port | Defaults to `587`. |
| `MAIL_USERNAME` / `EMAIL_HOST_USER` | SMTP username and sender address | Optional in local development. |
| `MAIL_PASSWORD` / `EMAIL_HOST_PASSWORD` | SMTP password | Optional in local development. |
| `MAIL_USE_TLS` / `EMAIL_USE_TLS` | Enable SMTP TLS | Defaults to `True`. |
| `OTP_EXPIRY_SECONDS` | OTP lifetime | Defaults to `600` seconds. |

The app also enforces a maximum request size of 6 MiB and a maximum individual upload size of 5 MiB. Medical report files allow PDF, DOC, DOCX, PNG, JPG, and JPEG extensions. Profile photos allow PNG, JPG, JPEG, and WEBP.

## Installation and setup

### 1. Create the MySQL database

Create the database configured by `DB_NAME` (the default is `ai_health_management`) and ensure the configured database user can create and alter tables.

### 2. Configure the environment

```powershell
Copy-Item .env.example .env
```

Edit `.env` and set your local database password and a unique `SECRET_KEY`. Remove or change any sample credentials before running the application.

### 3. Create and activate a virtual environment

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

On macOS or Linux, activate with:

```bash
source .venv/bin/activate
```

### 4. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Initialize the database and create an administrator

Importing `run.py` creates the Flask application and initializes tables (including supported legacy MySQL compatibility adjustments):

```bash
python -c "from run import app"
```

Create an administrator interactively:

```bash
flask --app run.py create-admin
```

The command prompts for the admin email, name, and password. It does not print or store a plaintext password.

## Run the application

```bash
python run.py
```

Open [http://127.0.0.1:5000/](http://127.0.0.1:5000/) for the site. The administrator login is at [http://127.0.0.1:5000/admin/login](http://127.0.0.1:5000/admin/login).

For local development, Flask can also run the same entry point:

```bash
flask --app run.py run --debug
```

Do not use Flask's development server as a production server. Deploy behind a production WSGI server and HTTPS-terminating reverse proxy, with `DEBUG=False`, a secure secret, secure cookies, and production-grade database and SMTP credentials.

## CLI commands

| Command | Description |
| --- | --- |
| `flask --app run.py create-admin` | Create an administrator interactively. |
| `flask --app run.py reset-admin-password` | Set a new password for an existing admin and invalidate their current sessions. |
| `flask --app run.py allow-duplicate-user-emails` | MySQL-only legacy utility that removes an existing unique index on `users.email`, if present. The current schema expects unique user emails; use this only when intentionally preserving a legacy installation that permits duplicates. |

## Data model and database

The application manages users, administrators, medicines, reminders, appointments, health records, medical reports, and feedback. Business identifiers are generated in Python and stored as `VARCHAR(20)` values with prefixes such as `USR`, `ADM`, `MED`, `REM`, `APP`, `HRC`, `REP`, and `FDB`; they are not auto-incrementing integers.

The schema uses foreign keys to associate patient-owned records with users. Health records are unique per user. Reminders can reference a medicine or appointment. User and admin email addresses are unique in the current schema. User-owned uploaded reports are associated with the owning user.

At startup, `initialize_database()` calls SQLAlchemy `create_all()` and applies compatibility adjustments for supported older MySQL schemas (for example, converting legacy integer identifiers and adding newer health record columns). This is a lightweight compatibility mechanism, not a general versioned migration system. Back up an existing database before upgrading and review `database.py` before applying startup changes to a production database.

## Uploads and privacy

Uploaded files are stored beneath the configured `UPLOAD_FOLDER` (by default, `app/uploads/`). Report files are placed in a user-specific directory. Authenticated users can access their own reports; administrators can access uploaded files through the guarded upload route. Upload validation checks allowed file extensions and size limits.

The application handles sensitive health and account information. For any deployment, restrict database and filesystem access, use HTTPS, set strong secrets, secure backups, and follow the privacy and retention requirements that apply to your organization and users. Do not commit uploaded data, `.env`, or database dumps.

## AI assistant

The AI endpoints require an authenticated user and an `OPENROUTER_API_KEY`. The assistant supports chat, recommendation, and summary modes; uploaded report summarization; and exporting the latest response to PDF, XLSX, or PNG. The API key remains server-side. The current AI helper reports provider unavailability to the user rather than crashing the site. AI output should be reviewed and should not be treated as medical advice.

AI features are optional. Without a key, the rest of the application can still be used, while AI requests may be unavailable.

## Email and password recovery

Password recovery uses a time-limited OTP. The code is held as hashed session data and is not stored in the users table. The configured SMTP server sends recovery messages when mail credentials are present. In development, when SMTP is not configured, OTP messages are printed to the application output; configure SMTP before enabling password recovery in a deployed environment.

## Development notes

- Blueprints are registered in `routes/__init__.py`; route implementations live in `routes/`.
- SQLAlchemy models live in `models/`, and shared database / CSRF objects are defined in `extensions.py`.
- Shared auth, validation, upload, OTP, email, AI, and reminder helpers live in `utils/`.
- Jinja templates and static assets live under `app/templates/` and `app/static/`.
- Forms use CSRF protection. Mutating actions generally use POST requests.
- Application errors have dedicated templates under `app/templates/errors/`.
- No automated test command is currently documented in this repository. When adding or changing behavior, add suitable tests and document the supported test workflow.

## Troubleshooting

### Database connection fails

Confirm that MySQL is running, the configured database exists, and `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, and `DB_PASSWORD` in `.env` match a user with access to that database.

### AI requests are unavailable

Check `OPENROUTER_API_KEY`, the configured model name, and outbound connectivity to the OpenRouter API. Core non-AI features do not require an API key.

### Recovery emails are not arriving

Check the SMTP host, port, TLS setting, username, password, sender address, and mail provider's authentication requirements. In development, check the server output for the fallback OTP message when SMTP credentials are not set.

### Existing database errors during startup

Back up the database, inspect the schema and startup migration logic in `database.py`, and confirm that the installation's legacy schema is one the compatibility adjustments support. Do not run the duplicate-email CLI command unless removing the email uniqueness constraint is intentional.

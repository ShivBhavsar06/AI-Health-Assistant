import os
from urllib.parse import quote_plus

from dotenv import load_dotenv

load_dotenv()


def _env_flag(name: str, default: bool = False) -> bool:
    """Read a boolean environment variable, falling back to ``default``."""
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _database_uri() -> str:
    """Build the SQLAlchemy URL, preferring an explicit ``DATABASE_URL``."""
    database_url = os.getenv("DATABASE_URL", "").strip()
    if database_url:
        return database_url

    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "3306")
    name = os.getenv("DB_NAME", "ai_health_management")
    user = os.getenv("DB_USER", "root")
    password = os.getenv("DB_PASSWORD", "0603")
    return (
        f"mysql+pymysql://{quote_plus(user)}:{quote_plus(password)}"
        f"@{host}:{port}/{name}"
    )


def _ai_endpoint() -> tuple[str, str]:
    """Pick the AI base URL and model, inferring the provider from the key prefix."""
    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    base_url = os.getenv("OPENROUTER_BASE_URL", "").strip()
    model = os.getenv("OPENROUTER_MODEL", "").strip()

    providers = {
        "gsk_": ("https://api.groq.com/openai/v1", "openai/gpt-oss-120b"),
        "AIza": ("https://generativelanguage.googleapis.com/v1beta/openai/", "gemini-2.5-flash"),
    }
    for prefix, (provider_base, provider_model) in providers.items():
        if not key.startswith(prefix):
            continue
        # A provider key paired with the default OpenRouter URL is a configuration mistake.
        if not base_url or "openrouter.ai" in base_url:
            base_url = provider_base
        if not model or model == "openai/gpt-4o-mini":
            model = provider_model
        break

    return base_url or "https://openrouter.ai/api/v1", model or "openai/gpt-4o-mini"


def _engine_options() -> dict:
    """Connection options, including TLS for managed MySQL providers."""
    options = {"pool_pre_ping": True}
    if os.getenv("DATABASE_URL", "").strip():
        return options

    ssl_ca = os.getenv("DB_SSL_CA", "").strip()
    ssl_require = _env_flag("DB_SSL_REQUIRE", False)
    ssl_verify = _env_flag("DB_SSL_VERIFY", True)
    if ssl_ca:
        options["connect_args"] = {
            "ssl": {"ca": ssl_ca, "check_hostname": ssl_verify, "verify_mode": ssl_verify}
        }
    elif ssl_require:
        # Encrypt the connection without pinning a CA certificate.
        options["connect_args"] = {
            "ssl": {"ca": None, "check_hostname": False, "verify_mode": False}
        }
    return options


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-change-this-secret-key")
    # Debugging is opt-in: only enable it when DEBUG is true or FLASK_ENV=development.
    DEBUG = _env_flag("DEBUG", os.getenv("FLASK_ENV", "").strip().lower() == "development")

    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "3306")
    DB_NAME = os.getenv("DB_NAME", "ai_health_management")
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "0603")

    SQLALCHEMY_DATABASE_URI = _database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = _engine_options()

    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None
    SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "healthmate_session")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _env_flag("SESSION_COOKIE_SECURE", not DEBUG)
    SESSION_REFRESH_EACH_REQUEST = True
    PERMANENT_SESSION_LIFETIME = int(os.getenv("REMEMBER_ME_DAYS", "30")) * 86400

    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
    OPENROUTER_BASE_URL, OPENROUTER_MODEL = _ai_endpoint()
    OPENROUTER_SITE_URL = os.getenv("OPENROUTER_SITE_URL", "")
    OPENROUTER_APP_NAME = os.getenv("OPENROUTER_APP_NAME", "HealthMate AI")

    EMAIL_HOST = os.getenv("EMAIL_HOST") or os.getenv("MAIL_SERVER", "")
    EMAIL_PORT = int(os.getenv("EMAIL_PORT") or os.getenv("MAIL_PORT", "587") or 587)
    EMAIL_HOST_USER = (
        os.getenv("EMAIL_HOST_USER")
        or os.getenv("MAIL_USERNAME")
        or os.getenv("EMAIL_USER", "")
    ).strip()
    EMAIL_HOST_PASSWORD = (
        os.getenv("EMAIL_HOST_PASSWORD")
        or os.getenv("MAIL_PASSWORD")
        or os.getenv("EMAIL_PASSWORD", "")
    ).replace(" ", "")
    EMAIL_USE_TLS = (os.getenv("EMAIL_USE_TLS") or os.getenv("MAIL_USE_TLS", "True")).lower() == "true"
    DEFAULT_FROM_EMAIL = (
        os.getenv("DEFAULT_FROM_EMAIL")
        or os.getenv("EMAIL_FROM")
        or os.getenv("EMAIL_HOST_USER")
        or os.getenv("MAIL_USERNAME")
        or os.getenv("EMAIL_USER")
        or "noreply@localhost"
    )

    OTP_EXPIRY_SECONDS = int(os.getenv("OTP_EXPIRY_SECONDS", "600") or 600)
    OTP_RESEND_SECONDS = 60
    OTP_MAX_ATTEMPTS = 5

    MAX_CONTENT_LENGTH = 6 * 1024 * 1024
    MAX_UPLOAD_SIZE = 5 * 1024 * 1024
    ALLOWED_REPORT_EXTENSIONS = {".pdf", ".doc", ".docx", ".png", ".jpg", ".jpeg"}
    ALLOWED_PHOTO_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}

    SITE_NAME = "HealthMate AI"
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")

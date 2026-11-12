import os
from urllib.parse import quote_plus

from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-change-this-secret-key")
    DEBUG = os.getenv("DEBUG", "True").lower() == "true"

    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "3306")
    DB_NAME = os.getenv("DB_NAME", "ai_health_management")
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "0603")

    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{quote_plus(DB_USER)}:{quote_plus(DB_PASSWORD)}"
        f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None
    SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "healthmate_session")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "False" if DEBUG else "True").lower() == "true"
    SESSION_REFRESH_EACH_REQUEST = True
    PERMANENT_SESSION_LIFETIME = int(os.getenv("REMEMBER_ME_DAYS", "30")) * 86400

    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
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
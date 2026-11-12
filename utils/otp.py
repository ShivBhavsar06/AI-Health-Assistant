import hashlib
import hmac
import secrets
import time

from flask import current_app, session


def _now() -> int:
    return int(time.time())


def generate_otp(length: int = 6) -> str:
    return f"{secrets.randbelow(10**length):0{length}d}"


def _hash_code(code: str) -> str:
    secret = current_app.config["SECRET_KEY"].encode()
    return hmac.new(secret, code.encode(), hashlib.sha256).hexdigest()


def _key(purpose: str) -> str:
    return f"otp_{purpose}"


def can_send_otp(purpose: str) -> bool:
    payload = session.get(_key(purpose)) or {}
    last_sent = int(payload.get("sent_at") or 0)
    cooldown = current_app.config.get("OTP_RESEND_SECONDS", 60)
    return _now() - last_sent >= cooldown


def store_otp(purpose: str, email: str, extra=None, code: str | None = None) -> str:
    otp = code or generate_otp()
    session[_key(purpose)] = {
        "email": (email or "").lower().strip(),
        "code_hash": _hash_code(otp),
        "expires_at": _now() + int(current_app.config.get("OTP_EXPIRY_SECONDS", 600)),
        "attempts": 0,
        "used": False,
        "sent_at": _now(),
        "extra": extra or {},
    }
    session.modified = True
    return otp


def verify_otp(purpose: str, email: str, code: str) -> tuple[bool, str, dict]:
    payload = session.get(_key(purpose))
    if not payload:
        return False, "OTP has expired. Please request a new OTP.", {}
    if payload.get("used"):
        return False, "OTP has expired. Please request a new OTP.", {}
    if payload.get("email") != (email or "").lower().strip():
        return False, "Invalid OTP. Please try again.", {}
    if _now() > int(payload.get("expires_at") or 0):
        session.pop(_key(purpose), None)
        return False, "OTP has expired. Please request a new OTP.", {}

    attempts = int(payload.get("attempts") or 0) + 1
    payload["attempts"] = attempts
    session[_key(purpose)] = payload
    session.modified = True
    max_attempts = int(current_app.config.get("OTP_MAX_ATTEMPTS", 5))
    if attempts > max_attempts:
        session.pop(_key(purpose), None)
        return False, "Too many invalid OTP attempts. Please request a new OTP.", {}

    expected = payload.get("code_hash") or ""
    if not hmac.compare_digest(expected, _hash_code((code or "").strip())):
        return False, "Invalid OTP. Please try again.", {}

    extra = payload.get("extra") or {}
    session.pop(_key(purpose), None)
    session.modified = True
    return True, "", extra


def clear_otp(purpose: str) -> None:
    session.pop(_key(purpose), None)
    session.modified = True

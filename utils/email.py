import smtplib
from email.message import EmailMessage

from flask import current_app


def send_email(to_address: str, subject: str, body: str) -> None:
    config = current_app.config
    host = (config.get("EMAIL_HOST") or "").strip()
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = config.get("DEFAULT_FROM_EMAIL") or "noreply@localhost"
    message["To"] = to_address
    message.set_content(body)

    user = (config.get("EMAIL_HOST_USER") or "").strip()
    password = (config.get("EMAIL_HOST_PASSWORD") or "").strip()

    if not host:
        print(f"[DEV EMAIL] To={to_address} Subject={subject}\n{body}")
        return

    if not user or not password:
        print(f"[DEV EMAIL] To={to_address} Subject={subject}\n{body}")
        return

    port = int(config.get("EMAIL_PORT") or 587)
    with smtplib.SMTP(host, port, timeout=20) as smtp:
        if config.get("EMAIL_USE_TLS"):
            smtp.starttls()
        smtp.login(user, password)
        smtp.send_message(message)


def send_otp_email(email: str, code: str, purpose_label: str) -> None:
    minutes = int(current_app.config.get("OTP_EXPIRY_SECONDS", 600)) // 60
    site = current_app.config.get("SITE_NAME")
    subject = f"{site} - {purpose_label} OTP"
    body = (
        f"Your one-time password is {code}.\n\n"
        f"This code expires in {minutes} minutes.\n"
        "If you did not request this, you can ignore this email."
    )
    send_email(email, subject, body)

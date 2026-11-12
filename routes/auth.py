from datetime import date

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import generate_password_hash

from extensions import db
from models.admin import Admin
from models.user import User
from utils.auth import current_admin, current_user
from utils.email import send_email, send_otp_email
from utils.id_generator import PREFIXES, assign_new_id
from utils.otp import can_send_otp, clear_otp, store_otp, verify_otp
from utils.validators import (
    is_strong_password,
    is_valid_email,
    is_valid_phone,
    is_valid_username,
    normalize_phone,
    parse_date,
)

auth_bp = Blueprint("auth", __name__)


def _login_redirect():
    if session.get("admin_id") and current_admin() is not None:
        return redirect(url_for("admin.dashboard"))
    if session.get("admin_id"):
        session.pop("admin_id", None)
    if session.get("user_id") and current_user() is not None:
        return redirect(url_for("user.dashboard"))
    if session.get("user_id"):
        session.pop("user_id", None)
    return None


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    redirect_response = _login_redirect()
    if redirect_response:
        return redirect_response
    form = {
        "full_name": "",
        "username": "",
        "email": "",
        "phone_number": "",
        "date_of_birth": "",
    }
    if request.method == "POST":
        form.update(
            {
                "full_name": (request.form.get("full_name") or "").strip(),
                "username": (request.form.get("username") or "").strip(),
                "email": (request.form.get("email") or "").strip().lower(),
                "phone_number": (request.form.get("phone_number") or "").strip(),
                "date_of_birth": (request.form.get("date_of_birth") or "").strip(),
            }
        )
        password = request.form.get("password") or ""
        confirm = request.form.get("confirm_password") or ""
        dob = parse_date(form["date_of_birth"])
        errors = []
        if not form["full_name"]:
            errors.append("Full name is required.")
        if not is_valid_username(form["username"]):
            errors.append("Username must be 3–50 letters, numbers, dots, hyphens, or underscores.")
        if not is_valid_email(form["email"]):
            errors.append("Enter a valid email address.")
        if not is_valid_phone(form["phone_number"], required=True):
            errors.append("Enter a valid phone number.")
        if dob is False:
            errors.append("Enter a valid date of birth.")
        elif dob and dob > date.today():
            errors.append("Date of birth cannot be in the future.")
        if not is_strong_password(password):
            errors.append("Password must be at least 8 characters and include a letter and a number.")
        if password != confirm:
            errors.append("Passwords do not match.")
        if User.query.filter(func.lower(User.username) == form["username"].lower()).first():
            errors.append("This username is already taken.")
        if User.query.filter(func.lower(User.email) == form["email"]).first():
            errors.append("This email is already registered.")
        if errors:
            for item in errors:
                flash(item, "danger")
            return render_template("auth/register.html", form=form)
        user = User(
            full_name=form["full_name"],
            username=form["username"],
            email=form["email"],
            phone_number=normalize_phone(form["phone_number"]),
            date_of_birth=dob,
        )
        user.set_password(password)
        assign_new_id(user, PREFIXES["user"], "user_id")
        try:
            db.session.add(user)
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            current_app.logger.exception("Unable to create user account")
            flash("We could not create your account. Please check your details and try again.", "danger")
            return render_template("auth/register.html", form=form)
        flash("Registration successful. Please log in with your password.", "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/register.html", form=form)


def _start_user_session(user):
    remember = request.form.get("remember_me") == "1"
    session.clear()
    session.permanent = remember
    session["user_id"] = user.user_id
    flash("Login successful.", "success")
    return redirect(url_for("user.dashboard"))


def _start_admin_session(admin):
    remember = request.form.get("remember_me") == "1"
    session.clear()
    session["admin_id"] = admin.admin_id
    session.permanent = remember
    flash("Login successful.", "success")
    return redirect(url_for("admin.dashboard"))


def _authenticate(identifier, password):
    identifier = (identifier or "").strip()
    password = password or ""
    if not identifier or not password:
        return None, "Enter your email or username and password."

    if "@" in identifier:
        email = identifier.lower()
        admin = Admin.query.filter(func.lower(Admin.email) == email).first()
        if admin and admin.check_password(password):
            return ("admin", admin), None
        matches = [
            user
            for user in User.query.filter(func.lower(User.email) == email).all()
            if user.check_password(password)
        ]
        if len(matches) == 1:
            return ("user", matches[0]), None
        if len(matches) > 1:
            return None, "More than one patient uses this email. Sign in with your username instead."
        return None, "Invalid email or password."

    user = User.query.filter(func.lower(User.username) == identifier.lower()).first()
    if user and user.check_password(password):
        return ("user", user), None
    return None, "Invalid username or password."


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    redirect_response = _login_redirect()
    if redirect_response:
        return redirect_response
    form = {"identifier": ""}
    if request.method == "POST":
        identifier = (request.form.get("identifier") or request.form.get("email") or "").strip()
        password = request.form.get("password") or ""
        form = {"identifier": identifier}
        account, error = _authenticate(identifier, password)
        if account:
            kind, record = account
            if kind == "admin":
                return _start_admin_session(record)
            return _start_user_session(record)
        flash(error, "danger")
        return render_template("auth/login.html", form=form)
    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        if not is_valid_email(email):
            flash("Enter a valid email address.", "danger")
            return render_template("auth/forgot_password.html")
        if not can_send_otp("reset"):
            flash("Please wait before requesting another OTP.", "warning")
            return render_template("auth/forgot_password.html")
        user = User.query.filter(func.lower(User.email) == email).first()
        if user:
            try:
                code = store_otp("reset", email)
                send_otp_email(email, code, "Password reset")
            except Exception:
                clear_otp("reset")
                current_app.logger.exception("Failed to send password reset OTP")
                flash("Unable to send OTP at this time. Please try again later.", "danger")
                return render_template("auth/forgot_password.html")
        session["pending_reset_email"] = email
        flash("If the email exists, an OTP has been sent.", "success")
        return redirect(url_for("auth.verify_reset_otp"))
    return render_template("auth/forgot_password.html")


@auth_bp.route("/forgot-password/verify-otp", methods=["GET", "POST"])
def verify_reset_otp():
    email = session.get("pending_reset_email")
    if not email:
        return redirect(url_for("auth.forgot_password"))
    if request.method == "POST":
        ok, message, _extra = verify_otp("reset", email, request.form.get("otp") or "")
        if not ok:
            flash(message, "danger")
            return render_template("auth/verify_reset_otp.html", email=email)
        session["reset_verified_email"] = email
        session.pop("pending_reset_email", None)
        return redirect(url_for("auth.recovery_options"))
    return render_template("auth/verify_reset_otp.html", email=email)


@auth_bp.route("/forgot-password/options", methods=["GET", "POST"])
def recovery_options():
    email = session.get("reset_verified_email")
    if not email:
        return redirect(url_for("auth.forgot_password"))
    if request.method == "POST":
        option = request.form.get("recovery_option")
        if option == "reset":
            return redirect(url_for("auth.reset_password"))
        if option == "account":
            user = User.query.filter(func.lower(User.email) == email.lower()).first()
            if user:
                try:
                    send_email(
                        user.email,
                        f"{current_app.config.get('SITE_NAME')} - Account information",
                        f"Username: {user.username}\n\nA password reset is available from the account recovery page.\n"
                        "For your security, your current password is never sent by email.",
                    )
                except Exception:
                    current_app.logger.exception("Failed to send account information email")
                    flash("We could not send the account information email. Please try again.", "danger")
                    return render_template("auth/recovery_options.html")
            session.pop("reset_verified_email", None)
            flash("Account information has been sent to your registered email.", "success")
            return redirect(url_for("auth.login"))
        flash("Choose a recovery option.", "danger")
    return render_template("auth/recovery_options.html")


@auth_bp.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    email = session.get("reset_verified_email")
    if not email:
        return redirect(url_for("auth.forgot_password"))
    if request.method == "POST":
        password = request.form.get("password") or ""
        confirm = request.form.get("confirm_password") or ""
        if not is_strong_password(password):
            flash("Password must be at least 8 characters and include a letter and a number.", "danger")
            return render_template("auth/reset_password.html")
        if password != confirm:
            flash("Passwords do not match.", "danger")
            return render_template("auth/reset_password.html")
        user = User.query.filter(func.lower(User.email) == email.lower()).first()
        if not user:
            flash("Account not found.", "danger")
            return redirect(url_for("auth.login"))
        user.password = generate_password_hash(password)
        try:
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            current_app.logger.exception("Unable to reset user password")
            flash("We could not reset your password. Please try again.", "danger")
            return render_template("auth/reset_password.html")
        session.pop("reset_verified_email", None)
        if request.form.get("send_confirmation") == "1":
            try:
                send_email(
                    user.email,
                    f"{current_app.config.get('SITE_NAME')} - Password reset confirmation",
                    f"Your password for {current_app.config.get('SITE_NAME')} was reset successfully.\n"
                    "For your security, your password is never included in email.",
                )
            except Exception:
                current_app.logger.exception("Failed to send password reset confirmation")
                flash("Password reset successfully, but the confirmation email could not be sent.", "warning")
                return redirect(url_for("auth.login"))
        flash("Password reset successfully.", "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/reset_password.html")

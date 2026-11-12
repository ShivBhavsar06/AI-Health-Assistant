from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from sqlalchemy import or_

from extensions import db
from models.appointment import Appointment
from models.feedback import Feedback
from models.health_record import HealthRecord
from models.medical_report import MedicalReport
from models.medicine import Medicine
from models.reminder import Reminder
from models.user import User
from utils.auth import current_user, login_required
from utils.files import delete_upload, save_upload
from utils.reminders import refresh_missed_reminders
from utils.validators import is_valid_email, is_valid_phone, is_valid_username, normalize_phone, parse_date

user_bp = Blueprint("user", __name__)


def _user_reminders(user_id):
    items = (
        Reminder.query.outerjoin(Medicine)
        .outerjoin(Appointment)
        .filter(or_(Medicine.user_id == user_id, Appointment.user_id == user_id))
        .all()
    )
    refresh_missed_reminders(items)
    db.session.commit()
    return items


def _activity_analytics(user):
    reminders = _user_reminders(user.user_id)
    status_counts = {"Pending": 0, "Completed": 0, "Missed": 0}
    for item in reminders:
        if item.status in status_counts:
            status_counts[item.status] += 1
    counts = {
        "medicines": Medicine.query.filter_by(user_id=user.user_id).count(),
        "appointments": Appointment.query.filter_by(user_id=user.user_id).count(),
        "reports": MedicalReport.query.filter_by(user_id=user.user_id).count(),
        "feedback": Feedback.query.filter_by(user_id=user.user_id).count(),
        "pending_reminders": status_counts["Pending"],
    }
    return {
        "counts": counts,
        "reminders": status_counts,
        "chart_activity": {
            "labels": ["Medicines", "Appointments", "Reports", "Pending reminders"],
            "values": [counts["medicines"], counts["appointments"], counts["reports"], counts["pending_reminders"]],
        },
        "chart_reminders": {
            "labels": ["Pending", "Completed", "Missed"],
            "values": [status_counts["Pending"], status_counts["Completed"], status_counts["Missed"]],
        },
    }


def _profile_page(user, edit_open=False):
    analytics = _activity_analytics(user)
    return render_template(
        "profile/profile.html",
        profile_user={
            "full_name": user.full_name,
            "username": user.username,
            "email": user.email,
            "phone_number": user.phone_number,
            "date_of_birth": user.date_of_birth,
            "gender": user.gender,
            "profile_photo": user.profile_photo,
            "emergency_contact_name": user.emergency_contact_name,
            "emergency_contact_relationship": user.emergency_contact_relationship,
            "emergency_contact_phone": user.emergency_contact_phone,
        },
        analytics=analytics["counts"],
        edit_open=edit_open,
    )


def _save_profile(user):
    full_name = (request.form.get("full_name") or "").strip()
    username = (request.form.get("username") or "").strip()
    email = (request.form.get("email") or "").strip().lower()
    phone = (request.form.get("phone_number") or "").strip()
    gender = request.form.get("gender") or ""
    dob = parse_date(request.form.get("date_of_birth") or "")
    errors = []
    if not full_name:
        errors.append("Full name is required.")
    if not is_valid_username(username):
        errors.append("Enter a valid username.")
    if not is_valid_email(email):
        errors.append("Enter a valid email address.")
    if not is_valid_phone(phone, required=True):
        errors.append("Enter a valid phone number.")
    if dob is False:
        errors.append("Enter a valid date of birth.")
    elif dob and dob > date.today():
        errors.append("Date of birth cannot be in the future.")
    if gender and gender not in {"Male", "Female", "Other"}:
        errors.append("Select a valid gender.")
    if User.query.filter(User.username == username, User.user_id != user.user_id).first():
        errors.append("This username is already taken.")
    if User.query.filter(User.email == email, User.user_id != user.user_id).first():
        errors.append("This email is already registered.")
    emergency_phone = (request.form.get("emergency_contact_phone") or "").strip()
    if not is_valid_phone(emergency_phone):
        errors.append("Enter a valid emergency contact phone number.")
    photo = request.files.get("profile_photo")
    new_photo_path = None
    if photo and photo.filename:
        try:
            from flask import current_app

            new_photo_path = save_upload(
                photo,
                "profiles",
                user.user_id,
                current_app.config["ALLOWED_PHOTO_EXTENSIONS"],
            )
        except ValueError as exc:
            errors.append(str(exc))
    if errors:
        if new_photo_path:
            delete_upload(new_photo_path)
        for item in errors:
            flash(item, "danger")
        return _profile_page(user, edit_open=True)
    user.full_name = full_name
    user.username = username
    user.email = email
    user.phone_number = normalize_phone(phone)
    user.date_of_birth = dob
    user.gender = gender or None
    user.emergency_contact_name = (request.form.get("emergency_contact_name") or "").strip() or None
    user.emergency_contact_relationship = (request.form.get("emergency_contact_relationship") or "").strip() or None
    user.emergency_contact_phone = normalize_phone(emergency_phone)
    if new_photo_path:
        if user.profile_photo:
            delete_upload(user.profile_photo)
        user.profile_photo = new_photo_path
    db.session.commit()
    flash("Profile updated successfully.", "success")
    return redirect(url_for("user.profile"))


@user_bp.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    today = date.today()
    reminders = _user_reminders(user.user_id)
    today_reminders = [
        item
        for item in reminders
        if item.reminder_type == "Medicine" and item.reminder_date == today and item.status != "Completed"
    ][:8]
    analytics = _activity_analytics(user)
    return render_template(
        "dashboard/home.html",
        user={"full_name": user.full_name, "email": user.email},
        medicine_count=analytics["counts"]["medicines"],
        appointment_count=analytics["counts"]["appointments"],
        reminder_count=analytics["counts"]["pending_reminders"],
        report_count=analytics["counts"]["reports"],
        feedback_count=analytics["counts"]["feedback"],
        health_record=HealthRecord.query.filter_by(user_id=user.user_id).first(),
        today_reminders=today_reminders,
        upcoming_appointments=Appointment.query.filter_by(user_id=user.user_id, status="Upcoming")
        .order_by(Appointment.appointment_date, Appointment.appointment_time)
        .limit(5)
        .all(),
        latest_feedback=Feedback.query.filter_by(user_id=user.user_id).order_by(Feedback.feedback_date.desc()).first(),
        chart_activity=analytics["chart_activity"],
        chart_reminders=analytics["chart_reminders"],
    )


@user_bp.route("/personal-information")
@user_bp.route("/personal-information/edit")
@user_bp.route("/profile/edit")
@login_required
def personal_information():
    return redirect(url_for("user.profile", edit=1))


@user_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user = current_user()
    if request.method == "POST":
        return _save_profile(user)
    return _profile_page(user, edit_open=request.args.get("edit") == "1")


@user_bp.route("/settings")
@login_required
def settings():
    user = current_user()
    analytics = _activity_analytics(user)
    return render_template(
        "profile/settings.html",
        profile_user=user,
        analytics=analytics["counts"],
    )


@user_bp.route("/account/delete", methods=["POST"])
@login_required
def delete_account():
    user = current_user()
    if user.profile_photo:
        delete_upload(user.profile_photo)
    db.session.delete(user)
    db.session.commit()
    session.clear()
    flash("Your account has been deleted.", "success")
    return redirect(url_for("main.home"))

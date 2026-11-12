from datetime import date
from decimal import Decimal, InvalidOperation
from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from sqlalchemy import func, or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload, load_only

from extensions import db
from models.admin import Admin
from models.appointment import Appointment
from models.feedback import Feedback
from models.health_record import HealthRecord
from models.medical_report import MedicalReport
from models.medicine import Medicine
from models.user import User
from utils.auth import admin_required, current_admin
from utils.files import delete_upload
from utils.id_generator import PREFIXES, assign_new_id
from utils.pagination import paginate_query
from utils.reminders import sync_appointment_reminder, sync_medicine_reminders
from utils.validators import (
    is_strong_password,
    is_valid_email,
    is_valid_phone,
    is_valid_username,
    normalize_phone,
    parse_date,
    parse_time,
)

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def _user_form_context(**extra):
    return extra


def _mask_allergy(value):
    if not value:
        return "—"
    text = str(value)
    visible_characters = min(3, max(0, len(text) - 1))
    return text[:visible_characters] + "*" * (len(text) - visible_characters)


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    return redirect(url_for("auth.login"))


@admin_bp.route("/logout", methods=["POST"])
@admin_required
def logout():
    session.clear()
    flash("Administrator logged out.", "success")
    return redirect(url_for("auth.login"))


@admin_bp.route("/")
@admin_required
def dashboard():
    appointment_status = dict(
        db.session.query(Appointment.status, func.count(Appointment.appointment_id))
        .group_by(Appointment.status)
        .all()
    )
    return render_template(
        "admin/dashboard.html",
        total_users=User.query.count(),
        total_medicines=Medicine.query.count(),
        total_appointments=Appointment.query.count(),
        total_feedback=Feedback.query.count(),
        total_reports=MedicalReport.query.count(),
        total_health_records=HealthRecord.query.count(),
        appointment_status=appointment_status,
        recent_users=User.query.order_by(User.created_at.desc()).limit(5).all(),
        recent_appointments=Appointment.query.options(joinedload(Appointment.user))
        .filter(Appointment.status == "Upcoming")
        .order_by(Appointment.appointment_date, Appointment.appointment_time)
        .limit(5)
        .all(),
        recent_feedback=Feedback.query.options(joinedload(Feedback.user))
        .order_by(Feedback.feedback_date.desc())
        .limit(5)
        .all(),
    )


@admin_bp.route("/settings", methods=["GET", "POST"])
@admin_required
def settings():
    admin = current_admin()
    form = {"full_name": admin.full_name, "email": admin.email}
    if request.method == "POST":
        action = request.form.get("action") or "profile"
        if action == "profile":
            full_name = (request.form.get("full_name") or "").strip()
            email = (request.form.get("email") or "").strip().lower()
            errors = []
            if not full_name:
                errors.append("Admin name is required.")
            if not is_valid_email(email):
                errors.append("Enter a valid email address.")
            if Admin.query.filter(Admin.email == email, Admin.admin_id != admin.admin_id).first():
                errors.append("That email is already in use.")
            form = {"full_name": full_name, "email": email}
            if errors:
                for error in errors:
                    flash(error, "danger")
            else:
                admin.full_name = full_name
                admin.email = email
                try:
                    db.session.commit()
                except SQLAlchemyError:
                    db.session.rollback()
                    current_app.logger.exception("Unable to update administrator profile")
                    flash("We could not update your account settings.", "danger")
                else:
                    flash("Administrator account settings updated.", "success")
                    return redirect(url_for("admin.settings"))
        elif action == "password":
            current_password = request.form.get("current_password") or ""
            new_password = request.form.get("new_password") or ""
            confirmation = request.form.get("confirm_password") or ""
            if not admin.check_password(current_password):
                flash("Your current password is incorrect.", "danger")
            elif not is_strong_password(new_password):
                flash("Password must be at least 8 characters and include a letter and a number.", "danger")
            elif new_password != confirmation:
                flash("Passwords do not match.", "danger")
            else:
                admin.set_password(new_password)
                try:
                    db.session.commit()
                except SQLAlchemyError:
                    db.session.rollback()
                    current_app.logger.exception("Unable to update administrator password")
                    flash("We could not update your password.", "danger")
                else:
                    flash("Administrator password updated successfully.", "success")
                    return redirect(url_for("admin.settings"))
        else:
            flash("Invalid settings action.", "danger")
    return render_template(
        "admin/settings.html",
        admin=admin,
        form=form,
        email_configured=bool(current_app.config.get("EMAIL_HOST")),
        ai_configured=bool(current_app.config.get("OPENROUTER_API_KEY")),
        session_cookie_secure=bool(current_app.config.get("SESSION_COOKIE_SECURE")),
        session_cookie_httponly=bool(current_app.config.get("SESSION_COOKIE_HTTPONLY")),
        session_lifetime_days=int(current_app.config.get("PERMANENT_SESSION_LIFETIME", 0) / 86400),
    )


@admin_bp.route("/users")
@admin_required
def users():
    q = (request.args.get("q") or "").strip()
    query = User.query
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                User.user_id.ilike(like),
                User.username.ilike(like),
                User.full_name.ilike(like),
                User.email.ilike(like),
            )
        )
    pagination = paginate_query(query.order_by(User.full_name))
    return render_template("admin/users.html", users=pagination.items, pagination=pagination, q=q)


@admin_bp.route("/users/add", methods=["GET", "POST"])
@admin_required
def add_user():
    if request.method == "POST":
        data, errors = _user_form_data(None)
        if errors:
            for item in errors:
                flash(item, "danger")
            return render_template("admin/user_form.html", **_user_form_context(account=None, form=request.form))
        user = User(
            full_name=data["full_name"],
            username=data["username"],
            email=data["email"],
            phone_number=data["phone_number"],
            date_of_birth=data["date_of_birth"],
            gender=data["gender"],
        )
        assign_new_id(user, PREFIXES["user"], "user_id")
        user.set_password(data["password"])
        db.session.add(user)
        db.session.commit()
        flash("User added successfully.", "success")
        return redirect(url_for("admin.users"))
    return render_template("admin/user_form.html", **_user_form_context(account=None, form={}))


@admin_bp.route("/users/<user_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_user(user_id):
    user = User.query.filter_by(user_id=user_id).first_or_404()
    if request.method == "POST":
        data, errors = _user_form_data(user)
        if errors:
            for item in errors:
                flash(item, "danger")
            return render_template("admin/user_form.html", **_user_form_context(account=user, form=request.form))
        user.full_name = data["full_name"]
        user.username = data["username"]
        user.email = data["email"]
        user.phone_number = data["phone_number"]
        user.date_of_birth = data["date_of_birth"]
        user.gender = data["gender"]
        if data["password"]:
            user.set_password(data["password"])
        db.session.commit()
        flash("User updated successfully.", "success")
        return redirect(url_for("admin.users"))
    return render_template("admin/user_form.html", **_user_form_context(account=user, form={}))


@admin_bp.route("/users/<user_id>/delete", methods=["POST"])
@admin_required
def delete_user(user_id):
    user = User.query.filter_by(user_id=user_id).first_or_404()
    db.session.delete(user)
    db.session.commit()
    flash("User deleted successfully.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/reports")
@admin_required
def reports():
    q = (request.args.get("q") or "").strip()
    query = MedicalReport.query.options(joinedload(MedicalReport.user))
    if q:
        like = f"%{q}%"
        query = query.outerjoin(User).filter(
            or_(
                MedicalReport.report_name.ilike(like),
                MedicalReport.report_type.ilike(like),
                User.full_name.ilike(like),
            )
        )
    pagination = paginate_query(query.order_by(MedicalReport.upload_date.desc()))
    return render_template("admin/reports.html", reports=pagination.items, pagination=pagination, q=q)


@admin_bp.route("/reports/<report_id>/delete", methods=["POST"])
@admin_required
def delete_report(report_id):
    report = MedicalReport.query.filter_by(report_id=report_id).first_or_404()
    delete_upload(report.file_path)
    db.session.delete(report)
    db.session.commit()
    flash("Medical report deleted successfully.", "success")
    return redirect(url_for("admin.reports"))


@admin_bp.route("/medicines")
@admin_required
def medicines():
    q = (request.args.get("q") or "").strip()
    query = Medicine.query.options(joinedload(Medicine.user))
    if q:
        like = f"%{q}%"
        query = query.outerjoin(User).filter(or_(Medicine.medicine_name.ilike(like), User.full_name.ilike(like)))
    pagination = paginate_query(query.order_by(Medicine.created_at.desc()))
    return render_template("admin/medicines.html", medicines=pagination.items, pagination=pagination, q=q)


@admin_bp.route("/medicines/add", methods=["GET", "POST"])
@admin_required
def add_medicine():
    if request.method == "POST":
        user = User.query.filter_by(user_id=request.form.get("user_id")).first()
        if not user:
            flash("Select a valid user.", "danger")
            return render_template("admin/medicine_form.html", medicine=None, users=User.query.all(), form=request.form)
        data, errors = _medicine_fields()
        if errors:
            for item in errors:
                flash(item, "danger")
            return render_template("admin/medicine_form.html", medicine=None, users=User.query.all(), form=request.form)
        medicine = Medicine(user_id=user.user_id, **data)
        assign_new_id(medicine, PREFIXES["medicine"], "medicine_id")
        db.session.add(medicine)
        db.session.flush()
        sync_medicine_reminders(medicine)
        db.session.commit()
        flash("Medicine added successfully.", "success")
        return redirect(url_for("admin.medicines"))
    return render_template("admin/medicine_form.html", medicine=None, users=User.query.all(), form={})


@admin_bp.route("/medicines/<medicine_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_medicine(medicine_id):
    medicine = Medicine.query.filter_by(medicine_id=medicine_id).first_or_404()
    if request.method == "POST":
        data, errors = _medicine_fields()
        if errors:
            for item in errors:
                flash(item, "danger")
            return render_template("admin/medicine_form.html", medicine=medicine, users=User.query.all(), form=request.form)
        for key, value in data.items():
            setattr(medicine, key, value)
        sync_medicine_reminders(medicine)
        db.session.commit()
        flash("Medicine updated successfully.", "success")
        return redirect(url_for("admin.medicines"))
    return render_template("admin/medicine_form.html", medicine=medicine, users=User.query.all(), form={})


@admin_bp.route("/medicines/<medicine_id>/delete", methods=["POST"])
@admin_required
def delete_medicine(medicine_id):
    medicine = Medicine.query.filter_by(medicine_id=medicine_id).first_or_404()
    db.session.delete(medicine)
    db.session.commit()
    flash("Medicine deleted successfully.", "success")
    return redirect(url_for("admin.medicines"))


@admin_bp.route("/appointments")
@admin_required
def appointments():
    q = (request.args.get("q") or "").strip()
    query = Appointment.query.options(joinedload(Appointment.user))
    if q:
        like = f"%{q}%"
        query = query.outerjoin(User).filter(
            or_(
                Appointment.doctor_name.ilike(like),
                Appointment.hospital_name.ilike(like),
                Appointment.purpose.ilike(like),
                User.full_name.ilike(like),
            )
        )
    pagination = paginate_query(
        query.order_by(Appointment.appointment_date.desc(), Appointment.appointment_time.desc())
    )
    return render_template(
        "admin/appointments.html",
        appointments=pagination.items,
        pagination=pagination,
        q=q,
    )


@admin_bp.route("/appointments/add", methods=["GET", "POST"])
@admin_required
def add_appointment():
    if request.method == "POST":
        user = User.query.filter_by(user_id=request.form.get("user_id")).first()
        if not user:
            flash("Select a valid user.", "danger")
            return render_template("admin/appointment_form.html", appointment=None, users=User.query.all(), form=request.form)
        data, errors = _appointment_fields()
        if errors:
            for item in errors:
                flash(item, "danger")
            return render_template("admin/appointment_form.html", appointment=None, users=User.query.all(), form=request.form)
        item = Appointment(user_id=user.user_id, **data)
        assign_new_id(item, PREFIXES["appointment"], "appointment_id")
        db.session.add(item)
        db.session.flush()
        sync_appointment_reminder(item)
        db.session.commit()
        flash("Appointment added successfully.", "success")
        return redirect(url_for("admin.appointments"))
    return render_template("admin/appointment_form.html", appointment=None, users=User.query.all(), form={})


@admin_bp.route("/appointments/<appointment_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_appointment(appointment_id):
    item = Appointment.query.filter_by(appointment_id=appointment_id).first_or_404()
    if request.method == "POST":
        data, errors = _appointment_fields()
        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template("admin/appointment_form.html", appointment=item, users=User.query.all(), form=request.form)
        for key, value in data.items():
            setattr(item, key, value)
        sync_appointment_reminder(item)
        db.session.commit()
        flash("Appointment updated successfully.", "success")
        return redirect(url_for("admin.appointments"))
    return render_template("admin/appointment_form.html", appointment=item, users=User.query.all(), form={})


@admin_bp.route("/appointments/<appointment_id>/delete", methods=["POST"])
@admin_required
def delete_appointment(appointment_id):
    item = Appointment.query.filter_by(appointment_id=appointment_id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    flash("Appointment deleted successfully.", "success")
    return redirect(url_for("admin.appointments"))


@admin_bp.route("/health-records")
@admin_required
def health_records():
    q = (request.args.get("q") or "").strip()
    query = HealthRecord.query
    if q:
        like = f"%{q}%"
        query = query.join(User).filter(or_(User.full_name.ilike(like), User.email.ilike(like), HealthRecord.blood_group.ilike(like)))
    pagination = paginate_query(
        query.options(
            load_only(
                HealthRecord.record_id,
                HealthRecord.user_id,
                HealthRecord.blood_group,
                HealthRecord.height,
                HealthRecord.weight,
                HealthRecord.allergies,
                HealthRecord.updated_at,
            ),
            joinedload(HealthRecord.user),
        ).order_by(HealthRecord.updated_at.desc())
    )
    records = [
        {
            "record_id": record.record_id,
            "user_id": record.user_id,
            "patient_name": record.user.full_name if record.user else record.user_id,
            "blood_group": record.blood_group,
            "height": record.height,
            "weight": record.weight,
            "allergies": _mask_allergy(record.allergies),
        }
        for record in pagination.items
    ]
    return render_template(
        "admin/health_records.html",
        records=records,
        q=q,
    )


@admin_bp.route("/health-records/<record_id>/delete", methods=["POST"])
@admin_required
def delete_health_record(record_id):
    record = HealthRecord.query.filter_by(record_id=record_id).first_or_404()
    db.session.delete(record)
    db.session.commit()
    flash("Health record deleted successfully.", "success")
    return redirect(url_for("admin.health_records"))


@admin_bp.route("/feedback")
@admin_required
def feedback():
    q = (request.args.get("q") or "").strip()
    query = Feedback.query.options(joinedload(Feedback.user))
    if q:
        like = f"%{q}%"
        filters = [Feedback.comments.ilike(like), User.full_name.ilike(like)]
        try:
            rating_search = Decimal(q)
        except InvalidOperation:
            pass
        else:
            if rating_search.is_finite():
                filters.append(Feedback.rating == rating_search)
        query = query.outerjoin(User).filter(or_(*filters))
    pagination = paginate_query(query.order_by(Feedback.feedback_date.desc()))
    return render_template("admin/feedback.html", entries=pagination.items, pagination=pagination, q=q)


@admin_bp.route("/feedback/<feedback_id>/delete", methods=["POST"])
@admin_required
def delete_feedback(feedback_id):
    item = Feedback.query.filter_by(feedback_id=feedback_id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    flash("Feedback deleted successfully.", "success")
    return redirect(url_for("admin.feedback"))


def _user_form_data(existing):
    full_name = (request.form.get("full_name") or "").strip()
    username = (request.form.get("username") or "").strip()
    email = (request.form.get("email") or "").strip().lower()
    phone = (request.form.get("phone_number") or "").strip()
    gender = request.form.get("gender") or ""
    password = request.form.get("password") or ""
    dob = parse_date(request.form.get("date_of_birth") or "")
    errors = []
    if not full_name:
        errors.append("Full name is required.")
    if not is_valid_username(username):
        errors.append("Enter a valid username.")
    if not is_valid_email(email):
        errors.append("Enter a valid email address.")
    if not is_valid_phone(phone):
        errors.append("Enter a valid phone number.")
    if dob is False:
        errors.append("Enter a valid date of birth.")
    elif dob and dob > date.today():
        errors.append("Date of birth cannot be in the future.")
    if gender and gender not in {"Male", "Female", "Other"}:
        errors.append("Select a valid gender.")
    username_q = User.query.filter(User.username == username)
    email_q = User.query.filter(User.email == email)
    if existing:
        username_q = username_q.filter(User.user_id != existing.user_id)
        email_q = email_q.filter(User.user_id != existing.user_id)
    if username_q.first():
        errors.append("This username is already taken.")
    if email_q.first():
        errors.append("This email is already registered.")
    if existing is None and not is_strong_password(password):
        errors.append("Password must be at least 8 characters and include a letter and a number.")
    if password and not is_strong_password(password):
        errors.append("Password must be at least 8 characters and include a letter and a number.")
    return {
        "full_name": full_name,
        "username": username,
        "email": email,
        "phone_number": normalize_phone(phone),
        "date_of_birth": dob if dob else None,
        "gender": gender or None,
        "password": password,
    }, errors


def _medicine_fields():
    errors = []
    name = (request.form.get("medicine_name") or "").strip()
    if not name:
        errors.append("Medicine name is required.")
    times = {}
    for field in ("morning_time", "afternoon_time", "evening_time", "night_time"):
        parsed = parse_time(request.form.get(field) or "")
        if parsed is False:
            errors.append("Enter valid reminder times.")
            break
        times[field] = parsed
    start = parse_date(request.form.get("start_date") or "")
    end = parse_date(request.form.get("end_date") or "")
    if start is False or end is False:
        errors.append("Enter valid dates.")
    if start and end and end < start:
        errors.append("End date cannot be before start date.")
    return {
        "medicine_name": name,
        "dosage": (request.form.get("dosage") or "").strip() or None,
        "instructions": (request.form.get("instructions") or "").strip() or None,
        "start_date": start if start else None,
        "end_date": end if end else None,
        **times,
    }, errors


def _appointment_fields():
    errors = []
    status = request.form.get("status") or "Upcoming"
    doctor = (request.form.get("doctor_name") or "").strip()
    if status not in {"Upcoming", "Completed", "Cancelled"}:
        errors.append("Select a valid status.")
    if not doctor:
        errors.append("Doctor name is required.")
    appt_date = parse_date(request.form.get("appointment_date") or "")
    appt_time = parse_time(request.form.get("appointment_time") or "")
    if appt_date is False:
        errors.append("Enter a valid appointment date.")
    if appt_time is False:
        errors.append("Enter a valid appointment time.")
    if appt_date is None:
        errors.append("Appointment date is required.")
    if appt_time is None:
        errors.append("Appointment time is required.")
    return {
        "doctor_name": doctor,
        "hospital_name": (request.form.get("hospital_name") or "").strip() or None,
        "purpose": (request.form.get("purpose") or "").strip() or None,
        "status": status,
        "appointment_date": appt_date,
        "appointment_time": appt_time,
    }, errors

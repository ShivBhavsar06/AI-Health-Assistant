from datetime import datetime, timedelta

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from sqlalchemy import or_

from extensions import db
from models.appointment import Appointment
from utils.auth import current_user, login_required
from utils.id_generator import PREFIXES, assign_new_id
from utils.reminders import sync_appointment_reminder
from utils.validators import parse_date, parse_time

appointments_bp = Blueprint("appointments", __name__, url_prefix="/appointments")


def _owned_appointment(appointment_id):
    user = current_user()
    item = Appointment.query.filter_by(appointment_id=appointment_id, user_id=user.user_id).first()
    if not item:
        abort(404)
    return item


def _collect_fields():
    errors = []
    doctor = (request.form.get("doctor_name") or "").strip()
    hospital = (request.form.get("hospital_name") or "").strip()
    purpose = (request.form.get("purpose") or "").strip()
    status = request.form.get("status") or "Upcoming"
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
    data = {
        "doctor_name": doctor,
        "hospital_name": hospital or None,
        "purpose": purpose or None,
        "status": status,
        "appointment_date": appt_date,
        "appointment_time": appt_time,
    }
    return data, errors


@appointments_bp.route("/")
@login_required
def list_appointments():
    user = current_user()
    q = (request.args.get("q") or "").strip()
    query = Appointment.query.filter_by(user_id=user.user_id)
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                Appointment.doctor_name.ilike(like),
                Appointment.hospital_name.ilike(like),
                Appointment.purpose.ilike(like),
            )
        )
    return render_template(
        "appointments/list.html",
        appointments=query.order_by(Appointment.appointment_date.desc()).all(),
        q=q,
    )


@appointments_bp.route("/add", methods=["GET", "POST"])
@login_required
def add():
    if request.method == "POST":
        data, errors = _collect_fields()
        if errors:
            for item in errors:
                flash(item, "danger")
            return render_template("appointments/form.html", appointment=None, form=request.form)
        user = current_user()
        item = Appointment(user_id=user.user_id, **data)
        assign_new_id(item, PREFIXES["appointment"], "appointment_id")
        db.session.add(item)
        db.session.flush()
        sync_appointment_reminder(item)
        db.session.commit()
        flash("Appointment added successfully.", "success")
        return redirect(url_for("appointments.list_appointments"))
    next_slot = datetime.now().replace(second=0, microsecond=0)
    next_slot += timedelta(minutes=30 - next_slot.minute % 30)
    return render_template(
        "appointments/form.html",
        appointment=None,
        form={
            "appointment_date": next_slot.date().isoformat(),
            "appointment_time": next_slot.strftime("%H:%M"),
        },
    )


@appointments_bp.route("/<appointment_id>/edit", methods=["GET", "POST"])
@login_required
def edit(appointment_id):
    item = _owned_appointment(appointment_id)
    if request.method == "POST":
        data, errors = _collect_fields()
        if errors:
            for item_error in errors:
                flash(item_error, "danger")
            return render_template("appointments/form.html", appointment=item, form=request.form)
        for key, value in data.items():
            setattr(item, key, value)
        sync_appointment_reminder(item)
        db.session.commit()
        flash("Appointment updated successfully.", "success")
        return redirect(url_for("appointments.list_appointments"))
    return render_template("appointments/form.html", appointment=item, form={})


@appointments_bp.route("/<appointment_id>/delete", methods=["POST"])
@login_required
def delete(appointment_id):
    item = _owned_appointment(appointment_id)
    db.session.delete(item)
    db.session.commit()
    flash("Appointment deleted successfully.", "success")
    return redirect(url_for("appointments.list_appointments"))

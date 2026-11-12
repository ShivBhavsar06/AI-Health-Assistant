from datetime import date

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from sqlalchemy import or_

from extensions import db
from models.medicine import Medicine
from utils.auth import current_user, login_required
from utils.id_generator import PREFIXES, assign_new_id
from utils.reminders import sync_medicine_reminders
from utils.validators import parse_date, parse_time

medicines_bp = Blueprint("medicines", __name__, url_prefix="/medicines")


def _owned_medicine(medicine_id):
    user = current_user()
    medicine = Medicine.query.filter_by(medicine_id=medicine_id, user_id=user.user_id).first()
    if not medicine:
        abort(404)
    return medicine


def _collect_medicine_fields():
    name = (request.form.get("medicine_name") or "").strip()
    dosage = (request.form.get("dosage") or "").strip()
    instructions = (request.form.get("instructions") or "").strip()
    errors = []
    if not name:
        errors.append("Medicine name is required.")
    selected_periods = set(request.form.getlist("dose_periods"))
    valid_periods = {"morning", "afternoon", "evening", "night"}
    if not selected_periods.issubset(valid_periods):
        errors.append("Select valid dose periods.")
    times = {}
    for field in ("morning_time", "afternoon_time", "evening_time", "night_time"):
        period = field.removesuffix("_time")
        if period not in selected_periods:
            times[field] = None
            continue
        parsed = parse_time(request.form.get(field) or "")
        if parsed is False:
            errors.append("Enter valid reminder times.")
            break
        if parsed is None:
            errors.append("Enter a time for each selected dose period.")
            continue
        times[field] = parsed
    start = parse_date(request.form.get("start_date") or "")
    end = parse_date(request.form.get("end_date") or "")
    if start is False or end is False:
        errors.append("Enter valid start and end dates.")
    if start and end and end < start:
        errors.append("End date cannot be before start date.")
    data = {
        "medicine_name": name,
        "dosage": dosage or None,
        "instructions": instructions or None,
        "start_date": start if start else None,
        "end_date": end if end else None,
        **times,
    }
    return data, errors


@medicines_bp.route("/")
@login_required
def list_medicines():
    user = current_user()
    q = (request.args.get("q") or "").strip()
    query = Medicine.query.filter_by(user_id=user.user_id)
    if q:
        query = query.filter(Medicine.medicine_name.ilike(f"%{q}%"))
    return render_template("medicines/list.html", medicines=query.order_by(Medicine.created_at.desc()).all(), q=q)


@medicines_bp.route("/add", methods=["GET", "POST"])
@login_required
def add_medicine():
    if request.method == "POST":
        data, errors = _collect_medicine_fields()
        if errors:
            for item in errors:
                flash(item, "danger")
            return render_template(
                "medicines/form.html",
                medicine=None,
                form=request.form,
                selected_periods=selected_periods,
            )
        user = current_user()
        medicine = Medicine(user_id=user.user_id, **data)
        assign_new_id(medicine, PREFIXES["medicine"], "medicine_id")
        db.session.add(medicine)
        db.session.flush()
        sync_medicine_reminders(medicine)
        db.session.commit()
        flash("Medicine added successfully.", "success")
        return redirect(url_for("medicines.list_medicines"))
    return render_template(
        "medicines/form.html",
        medicine=None,
        form={
            "start_date": date.today().isoformat(),
            "morning_time": "08:00",
            "afternoon_time": "12:00",
            "evening_time": "18:00",
            "night_time": "21:00",
        },
        selected_periods=set(),
    )


@medicines_bp.route("/<medicine_id>")
@login_required
def detail(medicine_id):
    return render_template("medicines/detail.html", medicine=_owned_medicine(medicine_id))


@medicines_bp.route("/<medicine_id>/edit", methods=["GET", "POST"])
@login_required
def edit(medicine_id):
    medicine = _owned_medicine(medicine_id)
    if request.method == "POST":
        data, errors = _collect_medicine_fields()
        if errors:
            for item in errors:
                flash(item, "danger")
            return render_template(
                "medicines/form.html",
                medicine=medicine,
                form=request.form,
                selected_periods=set(request.form.getlist("dose_periods")),
            )
        for key, value in data.items():
            setattr(medicine, key, value)
        sync_medicine_reminders(medicine)
        db.session.commit()
        flash("Medicine updated successfully.", "success")
        return redirect(url_for("medicines.detail", medicine_id=medicine.medicine_id))
    return render_template("medicines/form.html", medicine=medicine, form={})


@medicines_bp.route("/<medicine_id>/delete", methods=["POST"])
@login_required
def delete(medicine_id):
    medicine = _owned_medicine(medicine_id)
    db.session.delete(medicine)
    db.session.commit()
    flash("Medicine deleted successfully.", "success")
    return redirect(url_for("medicines.list_medicines"))

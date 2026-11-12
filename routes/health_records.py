from decimal import Decimal, InvalidOperation

from flask import Blueprint, flash, redirect, render_template, request, url_for

from extensions import db
from models.health_record import HealthRecord
from utils.auth import current_user, login_required
from utils.id_generator import PREFIXES, assign_new_id
from utils.validators import is_valid_measurement

health_records_bp = Blueprint("health_records", __name__, url_prefix="/health-record")


def _parse_decimal(value):
    value = (value or "").strip()
    if not value:
        return None
    try:
        number = Decimal(value)
    except InvalidOperation:
        return False
    return number


@health_records_bp.route("/")
@login_required
def detail():
    user = current_user()
    record = HealthRecord.query.filter_by(user_id=user.user_id).first()
    return render_template("health_records/detail.html", record=record)


@health_records_bp.route("/edit", methods=["GET", "POST"])
@login_required
def edit():
    user = current_user()
    record = HealthRecord.query.filter_by(user_id=user.user_id).first()
    if request.method == "POST":
        height = _parse_decimal(request.form.get("height"))
        weight = _parse_decimal(request.form.get("weight"))
        if height is False or weight is False or not is_valid_measurement(height) or not is_valid_measurement(weight):
            flash("Enter valid height and weight values.", "danger")
            return render_template("health_records/form.html", record=record)
        if record is None:
            record = HealthRecord(user_id=user.user_id)
            assign_new_id(record, PREFIXES["health_record"], "record_id")
            db.session.add(record)
        record.blood_group = (request.form.get("blood_group") or "").strip() or None
        record.height = height
        record.weight = weight
        record.allergies = (request.form.get("allergies") or "").strip() or None
        record.chronic_disease = (request.form.get("chronic_disease") or "").strip() or None
        record.smoking_status = (request.form.get("smoking_status") or "").strip() or None
        record.alcohol_use = (request.form.get("alcohol_use") or "").strip() or None
        record.exercise_habits = (request.form.get("exercise_habits") or "").strip() or None
        record.diet = (request.form.get("diet") or "").strip() or None
        record.other_lifestyle = (request.form.get("other_lifestyle") or "").strip() or None
        db.session.commit()
        flash("Health record updated successfully.", "success")
        return redirect(url_for("health_records.detail"))
    return render_template("health_records/form.html", record=record)


@health_records_bp.route("/delete", methods=["POST"])
@login_required
def delete():
    user = current_user()
    record = HealthRecord.query.filter_by(user_id=user.user_id).first()
    if record:
        db.session.delete(record)
        db.session.commit()
        flash("Health record deleted successfully.", "success")
    return redirect(url_for("health_records.detail"))

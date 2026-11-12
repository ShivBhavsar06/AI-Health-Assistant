from datetime import date

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for
from sqlalchemy import or_

from extensions import db
from models.appointment import Appointment
from models.medicine import Medicine
from models.reminder import Reminder
from utils.auth import current_user, login_required
from utils.reminders import due_reminder_payloads, refresh_missed_reminders, reminder_belongs_to_user

reminders_bp = Blueprint("reminders", __name__, url_prefix="/reminders")


def _user_reminders(user_id, reminder_date=None):
    query = (
        Reminder.query.outerjoin(Medicine)
        .outerjoin(Appointment)
        .filter(or_(Medicine.user_id == user_id, Appointment.user_id == user_id))
    )
    if reminder_date is not None:
        query = query.filter(Reminder.reminder_date == reminder_date)
    items = query.order_by(Reminder.reminder_date, Reminder.reminder_time).all()
    refresh_missed_reminders(items)
    db.session.commit()
    return items


@reminders_bp.route("/")
@login_required
def list_reminders():
    user = current_user()
    today = date.today()
    show_all = request.args.get("view", "today").lower() == "all"
    items = _user_reminders(user.user_id, reminder_date=None if show_all else today)
    group_key = "all" if show_all else "today"
    groups = {group_key: items}
    reminder_total = len(items)
    return render_template(
        "reminders/list.html",
        groups=groups,
        reminder_total=reminder_total,
        show_all=show_all,
    )


@reminders_bp.route("/due")
@login_required
def due_reminders():
    user = current_user()
    items = _user_reminders(user.user_id)
    payloads = due_reminder_payloads(items)
    for item in payloads:
        item["complete_url"] = url_for("reminders.complete", reminder_id=item["id"])
    return jsonify({"reminders": payloads, "count": len(payloads)})


def _wants_json():
    requested = request.headers.get("X-Requested-With", "")
    if requested.lower() == "xmlhttprequest":
        return True
    best = request.accept_mimetypes.best_match(["application/json", "text/html"])
    return best == "application/json"


@reminders_bp.route("/<reminder_id>/complete", methods=["POST"])
@login_required
def complete(reminder_id):
    user = current_user()
    reminder = Reminder.query.filter_by(reminder_id=reminder_id).first()
    if not reminder or not reminder_belongs_to_user(reminder, user.user_id):
        abort(404)
    reminder.status = "Completed"
    db.session.commit()
    if _wants_json():
        return jsonify({"ok": True, "id": reminder.reminder_id})
    flash("Reminder marked as completed.", "success")
    return redirect(url_for("reminders.list_reminders"))


@reminders_bp.route("/delete-all", methods=["POST"])
@login_required
def delete_all():
    user = current_user()
    items = _user_reminders(user.user_id)
    ids = [item.reminder_id for item in items]
    deleted = 0
    if ids:
        deleted = Reminder.query.filter(Reminder.reminder_id.in_(ids)).delete(synchronize_session=False)
        db.session.commit()
    if deleted:
        flash(f"Deleted {deleted} reminder{'s' if deleted != 1 else ''}.", "success")
    else:
        flash("There were no reminders to delete.", "info")
    return redirect(url_for("reminders.list_reminders"))

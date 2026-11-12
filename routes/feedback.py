from decimal import Decimal, InvalidOperation

from flask import Blueprint, flash, redirect, render_template, request, url_for

from extensions import db
from models.feedback import Feedback
from utils.auth import current_user, login_required
from utils.id_generator import PREFIXES, assign_new_id

feedback_bp = Blueprint("feedback", __name__, url_prefix="/feedback")


def _parse_rating(value):
    try:
        rating = Decimal((value or "").strip())
    except (InvalidOperation, ValueError):
        return None
    if rating < Decimal("1") or rating > Decimal("5") or (rating * 2) % 1:
        return None
    return rating


@feedback_bp.route("/", methods=["GET", "POST"])
@login_required
def create():
    user = current_user()
    entries = Feedback.query.filter_by(user_id=user.user_id).order_by(Feedback.feedback_date.desc()).all()
    if request.method == "POST":
        rating = _parse_rating(request.form.get("rating"))
        comments = (request.form.get("comments") or "").strip()
        if rating is None:
            flash("Rating must be between 1 and 5 in half-star increments.", "danger")
            return render_template(
                "feedback/form.html",
                entries=entries,
                submitted_rating=request.form.get("rating"),
                submitted_comments=comments,
            )
        item = Feedback(user_id=user.user_id, rating=rating, comments=comments or None)
        assign_new_id(item, PREFIXES["feedback"], "feedback_id")
        db.session.add(item)
        db.session.commit()
        flash("Feedback submitted successfully.", "success")
        return redirect(url_for("feedback.create"))
    return render_template("feedback/form.html", entries=entries, editing=None)


@feedback_bp.route("/<feedback_id>/edit", methods=["GET", "POST"])
@login_required
def edit(feedback_id):
    user = current_user()
    item = Feedback.query.filter_by(feedback_id=feedback_id, user_id=user.user_id).first_or_404()
    entries = Feedback.query.filter_by(user_id=user.user_id).order_by(Feedback.feedback_date.desc()).all()
    if request.method == "POST":
        rating = _parse_rating(request.form.get("rating"))
        comments = (request.form.get("comments") or "").strip()
        if rating is None:
            flash("Rating must be between 1 and 5 in half-star increments.", "danger")
            return render_template(
                "feedback/form.html",
                entries=entries,
                editing=item,
                submitted_rating=request.form.get("rating"),
                submitted_comments=comments,
            )
        item.rating = rating
        item.comments = comments or None
        db.session.commit()
        flash("Feedback updated successfully.", "success")
        return redirect(url_for("feedback.create"))
    return render_template("feedback/form.html", entries=entries, editing=item)


@feedback_bp.route("/<feedback_id>/delete", methods=["POST"])
@login_required
def delete(feedback_id):
    user = current_user()
    item = Feedback.query.filter_by(feedback_id=feedback_id, user_id=user.user_id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    flash("Feedback deleted successfully.", "success")
    return redirect(url_for("feedback.create"))

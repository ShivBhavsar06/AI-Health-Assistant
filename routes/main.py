from flask import Blueprint, current_app, flash, render_template, request

from models.feedback import Feedback
from utils.email import send_email
from utils.validators import is_valid_email

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def home():
    feedback_entries = (
        Feedback.query.filter(Feedback.comments.isnot(None), Feedback.comments != "")
        .order_by(Feedback.feedback_date.desc())
        .limit(6)
        .all()
    )
    return render_template("home.html", feedback_entries=feedback_entries)


@main_bp.route("/about")
def about():
    return render_template("about.html")


@main_bp.route("/contact", methods=["GET", "POST"])
def contact():
    form = {"name": "", "email": "", "message": ""}
    if request.method == "POST":
        form = {
            "name": (request.form.get("name") or "").strip(),
            "email": (request.form.get("email") or "").strip().lower(),
            "message": (request.form.get("message") or "").strip(),
        }
        errors = []
        if not form["name"] or len(form["name"]) > 100:
            errors.append("Enter your name.")
        if not is_valid_email(form["email"]):
            errors.append("Enter a valid email address.")
        if not form["message"] or len(form["message"]) > 2000:
            errors.append("Enter a message of up to 2,000 characters.")
        if errors:
            for item in errors:
                flash(item, "danger")
            return render_template("contact.html", form=form)
        destination = current_app.config.get("DEFAULT_FROM_EMAIL") or current_app.config.get("EMAIL_HOST_USER")
        body = (
            f"Name: {form['name']}\n"
            f"Email: {form['email']}\n\n"
            f"{form['message']}"
        )
        try:
            send_email(destination, "HealthMate AI contact form", body)
        except Exception:
            current_app.logger.exception("Unable to send contact message")
            flash("We could not send your message right now. Please try again later.", "danger")
            return render_template("contact.html", form=form)
        flash("Thank you. Your message has been sent.", "success")
        return render_template("contact.html", form={"name": "", "email": "", "message": ""})
    return render_template("contact.html", form=form)


@main_bp.route("/medical-disclaimer")
def medical_disclaimer():
    return render_template("legal/medical_disclaimer.html")


@main_bp.route("/privacy-policy")
def privacy_policy():
    return render_template("legal/privacy_policy.html")


@main_bp.route("/terms-of-use")
def terms_of_use():
    return render_template("legal/terms_of_use.html")

import os

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, send_file, url_for
from sqlalchemy import or_

from extensions import db
from models.medical_report import MedicalReport
from utils.auth import current_user, login_required
from utils.files import absolute_upload_path, delete_upload, save_upload
from utils.id_generator import PREFIXES, assign_new_id

medical_reports_bp = Blueprint("medical_reports", __name__, url_prefix="/medical-reports")


def _owned_report(report_id):
    user = current_user()
    report = MedicalReport.query.filter_by(report_id=report_id, user_id=user.user_id).first()
    if not report:
        abort(404)
    return report


@medical_reports_bp.route("/")
@login_required
def list_reports():
    user = current_user()
    q = (request.args.get("q") or "").strip()
    query = MedicalReport.query.filter_by(user_id=user.user_id)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(MedicalReport.report_name.ilike(like), MedicalReport.report_type.ilike(like)))
    return render_template(
        "medical_reports/list.html",
        reports=query.order_by(MedicalReport.upload_date.desc()).all(),
        q=q,
    )


@medical_reports_bp.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    user = current_user()
    if request.method == "POST":
        report_name = (request.form.get("report_name") or "").strip()
        if not report_name:
            flash("Report name is required.", "danger")
            return render_template("medical_reports/form.html", report=None)
        report = MedicalReport(
            user_id=user.user_id,
            report_name=report_name,
            report_type=(request.form.get("report_type") or "").strip() or None,
            description=(request.form.get("description") or "").strip() or None,
        )
        assign_new_id(report, PREFIXES["medical_report"], "report_id")
        try:
            report.file_path = save_upload(
                request.files.get("file"),
                f"reports/{user.user_id}",
                report.report_id,
                current_app.config["ALLOWED_REPORT_EXTENSIONS"],
            )
        except ValueError as exc:
            flash(str(exc), "danger")
            return render_template("medical_reports/form.html", report=None)
        db.session.add(report)
        db.session.commit()
        flash("Medical report uploaded successfully.", "success")
        return redirect(url_for("medical_reports.list_reports"))
    return render_template("medical_reports/form.html", report=None)


@medical_reports_bp.route("/<report_id>")
@login_required
def detail(report_id):
    return render_template("medical_reports/detail.html", report=_owned_report(report_id))


@medical_reports_bp.route("/<report_id>/edit", methods=["GET", "POST"])
@login_required
def edit(report_id):
    report = _owned_report(report_id)
    if request.method == "POST":
        report_name = (request.form.get("report_name") or "").strip()
        if not report_name:
            flash("Report name is required.", "danger")
            return render_template("medical_reports/form.html", report=report)
        report.report_name = report_name
        report.report_type = (request.form.get("report_type") or "").strip() or None
        report.description = (request.form.get("description") or "").strip() or None
        file_storage = request.files.get("file")
        if file_storage and file_storage.filename:
            try:
                new_path = save_upload(
                    file_storage,
                    f"reports/{report.user_id}",
                    report.report_id,
                    current_app.config["ALLOWED_REPORT_EXTENSIONS"],
                )
                delete_upload(report.file_path)
                report.file_path = new_path
            except ValueError as exc:
                flash(str(exc), "danger")
                return render_template("medical_reports/form.html", report=report)
        db.session.commit()
        flash("Medical report updated successfully.", "success")
        return redirect(url_for("medical_reports.detail", report_id=report.report_id))
    return render_template("medical_reports/form.html", report=report)


@medical_reports_bp.route("/<report_id>/file")
@login_required
def download(report_id):
    report = _owned_report(report_id)
    path = absolute_upload_path(report.file_path)
    if not path or not os.path.isfile(path):
        abort(404)
    return send_file(path, as_attachment=False)


@medical_reports_bp.route("/<report_id>/delete", methods=["POST"])
@login_required
def delete(report_id):
    report = _owned_report(report_id)
    delete_upload(report.file_path)
    db.session.delete(report)
    db.session.commit()
    flash("Medical report deleted successfully.", "success")
    return redirect(url_for("medical_reports.list_reports"))

from flask import Blueprint, Response, current_app, jsonify, render_template, request, session

from utils.ai import (
    UNAVAILABLE_MESSAGE,
    ask_health_assistant,
    build_ai_excel,
    build_ai_image,
    build_ai_pdf,
    summarize_uploaded_report,
)
from utils.auth import current_user, login_required

ai_bp = Blueprint("ai", __name__, url_prefix="/ai")


@ai_bp.route("/")
@login_required
def chat():
    return render_template("ai_assistant/chat.html")


@ai_bp.route("/query", methods=["POST"])
@login_required
def query():
    try:
        payload = request.get_json(silent=True) or {}
    except Exception:
        payload = {}
    if not payload:
        payload = request.form
    text = (payload.get("query") or "").strip()
    mode = payload.get("mode") or "chat"
    if mode not in {"chat", "recommend", "summary"}:
        mode = "chat"
    user = current_user()
    ok, message = ask_health_assistant(user, text, mode=mode)
    status = 200 if ok else 503
    if message == "Please enter a health-related question." or message.startswith("Your question"):
        status = 400
    session["ai_last_response"] = message if ok else ""
    return jsonify({"ok": ok, "response": message, "stored": False}), status


@ai_bp.route("/summarize-report", methods=["POST"])
@login_required
def summarize_report():
    try:
        ok, message = summarize_uploaded_report(current_user(), request.files.get("report"))
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    status = 200 if ok else 503
    if ok:
        session["ai_last_response"] = message
    return jsonify({"ok": ok, "response": message}), status


@ai_bp.route("/export-pdf", methods=["POST"])
@login_required
def export_pdf():
    text = (request.form.get("response") or session.get("ai_last_response") or "").strip()
    if not text:
        return jsonify({"ok": False, "error": "No AI response to export."}), 400
    user = current_user()
    pdf = build_ai_pdf(text, user.full_name)
    return Response(
        pdf,
        mimetype="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="ai-health-response.pdf"'},
    )


def _export_text():
    text = (request.form.get("response") or session.get("ai_last_response") or "").strip()
    if not text:
        return None, jsonify({"ok": False, "error": "No AI response to export."}), 400
    return text, None, None


@ai_bp.route("/export-excel", methods=["POST"])
@login_required
def export_excel():
    text, error, status = _export_text()
    if error:
        return error, status
    user = current_user()
    return Response(
        build_ai_excel(text, user.full_name),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="ai-health-response.xlsx"'},
    )


@ai_bp.route("/export-image", methods=["POST"])
@login_required
def export_image():
    text, error, status = _export_text()
    if error:
        return error, status
    user = current_user()
    return Response(
        build_ai_image(text, user.full_name),
        mimetype="image/png",
        headers={"Content-Disposition": 'attachment; filename="ai-health-response.png"'},
    )

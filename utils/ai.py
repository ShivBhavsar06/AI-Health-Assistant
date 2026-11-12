import base64
import mimetypes
import os
from io import BytesIO
from datetime import datetime

from flask import current_app

from models.appointment import Appointment
from models.health_record import HealthRecord
from models.medical_report import MedicalReport
from models.medicine import Medicine
from models.reminder import Reminder

UNAVAILABLE_MESSAGE = "The AI assistant is temporarily unavailable. Please try again later."
NOT_CONFIGURED_MESSAGE = "AI features are not enabled on this deployment."
AUTHENTICATION_MESSAGE = (
    "The AI provider rejected the API key. OPENROUTER_API_KEY must belong to the provider set in "
    "OPENROUTER_BASE_URL, and OPENROUTER_MODEL must be a model that provider offers."
)
RATE_LIMIT_MESSAGE = "The assistant is busy right now. Please wait a moment and try again."
TIMEOUT_MESSAGE = "The assistant took too long to respond. Please try again."
MODEL_MESSAGE = (
    "The configured AI model is not available for this API key. "
    "Set OPENROUTER_MODEL to a model your provider supports."
)


def _ai_client():
    """Build an OpenAI-compatible client from the current provider settings."""
    from openai import OpenAI

    headers = {}
    if current_app.config.get("OPENROUTER_SITE_URL"):
        headers["HTTP-Referer"] = current_app.config["OPENROUTER_SITE_URL"]
    if current_app.config.get("OPENROUTER_APP_NAME"):
        headers["X-Title"] = current_app.config["OPENROUTER_APP_NAME"]

    return OpenAI(
        api_key=current_app.config.get("OPENROUTER_API_KEY"),
        base_url=current_app.config.get("OPENROUTER_BASE_URL") or "https://openrouter.ai/api/v1",
        timeout=20.0,
        max_retries=0,
        default_headers=headers or None,
    )


def _ai_error_message(exc: Exception) -> str:
    """Map provider errors to a user-facing message.

    Providers disagree on status codes (a bad Gemini key returns 400 rather than
    401), so inspect both the code and the message text.
    """
    status = getattr(exc, "status_code", None)
    text = str(exc).lower()
    auth_markers = (
        "invalid api key",
        "api key not valid",
        "valid api key",
        "api key is invalid",
        "incorrect api key",
        "invalid_api_key",
        "unauthorized",
    )
    if status in (401, 403) or any(marker in text for marker in auth_markers):
        return AUTHENTICATION_MESSAGE
    if status == 429 or "rate limit" in text or "rate_limit" in text or "quota" in text:
        return RATE_LIMIT_MESSAGE
    if status == 404 or "model" in text and any(
        marker in text for marker in ("not found", "does not exist", "not supported", "invalid model")
    ):
        return MODEL_MESSAGE
    if getattr(exc, "status_code", None) is None and ("timeout" in text or "timed out" in text):
        return TIMEOUT_MESSAGE
    return UNAVAILABLE_MESSAGE

SYSTEM_PROMPT = (
    "You are a general health information assistant for the AI Personal Health and Medicine "
    "Management System. You are not a doctor and must not claim to diagnose, prescribe, or replace "
    "professional medical care. For serious or emergency symptoms, advise the user to seek "
    "appropriate professional medical assistance. Keep answers focused on health. If the question "
    "is unrelated to health, politely explain that you only provide health-related assistance. "
    "Use only the provided current-user context. Do not invent records the user does not have."
)

REPORT_TEXT_LIMIT = 24000
AI_RESPONSE_STYLE = (
    "Use concise, plain-language responses. Start with the direct answer, then use short "
    "paragraphs or simple hyphen bullets when helpful. Do not use Markdown bold or include "
    "double-asterisk markers. Avoid unnecessary introductions and sign-offs."
)


def _clean_ai_response(text: str) -> str:
    return (text or "").replace("**", "").strip()


def _report_text(file_storage):
    if not file_storage or not file_storage.filename:
        raise ValueError("Please choose a report to summarize.")

    extension = os.path.splitext(file_storage.filename)[1].lower()
    allowed = current_app.config.get("ALLOWED_REPORT_EXTENSIONS", set())
    if extension not in allowed:
        raise ValueError("Unsupported report type. Use PDF, DOCX, PNG, JPG, or JPEG.")

    file_storage.stream.seek(0, os.SEEK_END)
    size = file_storage.stream.tell()
    file_storage.stream.seek(0)
    if size > current_app.config.get("MAX_UPLOAD_SIZE", 5 * 1024 * 1024):
        raise ValueError("File is too large. Maximum size is 5 MB.")
    if extension == ".doc":
        raise ValueError("Legacy .doc files are not supported. Please save the Word file as .docx and try again.")

    content = file_storage.read()
    if extension == ".pdf":
        from pypdf import PdfReader

        pages = PdfReader(BytesIO(content)).pages
        text = "\n".join(page.extract_text() or "" for page in pages).strip()
        if not text:
            raise ValueError("This PDF has no readable text. Upload a text-based PDF or an image instead.")
        return {"kind": "text", "content": text[:REPORT_TEXT_LIMIT]}
    if extension == ".docx":
        from docx import Document

        document = Document(BytesIO(content))
        paragraphs = [paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip()]
        tables = [
            " | ".join(cell.text.strip() for cell in row.cells)
            for table in document.tables
            for row in table.rows
        ]
        text = "\n".join(paragraphs + tables).strip()
        if not text:
            raise ValueError("This Word document has no readable text.")
        return {"kind": "text", "content": text[:REPORT_TEXT_LIMIT]}

    media_type = mimetypes.guess_type(file_storage.filename)[0] or "image/jpeg"
    encoded = base64.b64encode(content).decode("ascii")
    return {"kind": "image", "content": f"data:{media_type};base64,{encoded}"}


def summarize_uploaded_report(user, file_storage):
    report = _report_text(file_storage)
    api_key = current_app.config.get("OPENROUTER_API_KEY")
    if not api_key:
        return False, NOT_CONFIGURED_MESSAGE

    instruction = (
        "Summarize this uploaded medical report for the patient in plain language. "
        "Identify the report type/date if visible, key findings, abnormal or noteworthy values, "
        "and questions the patient may ask a clinician. Do not diagnose, prescribe, or invent "
        "missing information. State clearly when something is unreadable."
    )
    if report["kind"] == "text":
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "system", "content": instruction},
            {"role": "user", "content": f"Patient name: {user.full_name}\nReport content:\n{report['content']}"},
        ]
    else:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "system", "content": instruction},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"Patient name: {user.full_name}. Summarize this report image."},
                    {"type": "image_url", "image_url": {"url": report["content"]}},
                ],
            },
        ]

    try:
        client = _ai_client()
        response = client.chat.completions.create(
            model=current_app.config.get("OPENROUTER_MODEL") or "openai/gpt-4o-mini",
            messages=messages,
            temperature=0.2,
            max_tokens=900,
        )
        content = (response.choices[0].message.content or "").strip()
        return (True, content) if content else (False, UNAVAILABLE_MESSAGE)
    except Exception as exc:
        message = _ai_error_message(exc)
        if message is UNAVAILABLE_MESSAGE:
            current_app.logger.exception("AI report summary request failed")
        else:
            current_app.logger.warning("AI report summary request failed: %s", exc)
        return False, message


def _relevant_context(user, query: str, include_health_record: bool = True) -> str:
    text = (query or "").lower()
    parts = []
    wants_medicine = any(
        word in text for word in ["medicine", "dose", "dosage", "tablet", "reminder", "schedule", "pill"]
    )
    wants_appointment = any(word in text for word in ["appointment", "doctor", "hospital", "visit", "clinic"])
    wants_record = include_health_record and any(
        word in text for word in ["blood", "weight", "height", "allerg", "chronic", "health record", "bmi"]
    )
    wants_report = any(word in text for word in ["report", "lab", "scan", "prescription file"])
    wants_summary = any(word in text for word in ["summary", "overview", "recommend", "recommendation"])

    if wants_summary or not any([wants_medicine, wants_appointment, wants_record, wants_report]):
        wants_medicine = wants_appointment = True
        wants_record = include_health_record

    if wants_medicine:
        meds = Medicine.query.filter_by(user_id=user.user_id).all()
        if meds:
            lines = []
            for med in meds:
                lines.append(
                    f"{med.medicine_name} dosage={med.dosage or 'n/a'} "
                    f"morning={med.morning_time or '-'} afternoon={med.afternoon_time or '-'} "
                    f"evening={med.evening_time or '-'} night={med.night_time or '-'}"
                )
            parts.append("Medicines:\n" + "\n".join(lines))
        today = datetime.now().date()
        reminders = (
            Reminder.query.join(Medicine, Reminder.medicine_id == Medicine.medicine_id)
            .filter(Medicine.user_id == user.user_id, Reminder.reminder_date == today)
            .limit(10)
            .all()
        )
        if reminders:
            parts.append(
                "Today medicine reminders:\n"
                + "\n".join(
                    f"{r.reminder_time} {r.status} ({r.medicine.medicine_name if r.medicine else ''})"
                    for r in reminders
                )
            )

    if wants_appointment:
        appts = (
            Appointment.query.filter_by(user_id=user.user_id)
            .filter(Appointment.status != "Cancelled")
            .limit(8)
            .all()
        )
        if appts:
            parts.append(
                "Appointments:\n"
                + "\n".join(
                    f"{a.appointment_date} {a.appointment_time} {a.doctor_name} {a.hospital_name} ({a.status})"
                    for a in appts
                )
            )

    if wants_record:
        record = HealthRecord.query.filter_by(user_id=user.user_id).first()
        if record:
            parts.append(
                "Health record: "
                f"blood_group={record.blood_group or 'n/a'}, height={record.height or 'n/a'}, "
                f"weight={record.weight or 'n/a'}, allergies={record.allergies or 'none'}, "
                f"chronic={record.chronic_disease or 'none'}"
            )

    if wants_report:
        reports = MedicalReport.query.filter_by(user_id=user.user_id).limit(8).all()
        if reports:
            parts.append(
                "Medical report names only:\n"
                + "\n".join(f"{r.report_name} ({r.report_type})" for r in reports)
            )
    return "\n".join(parts)


def ask_health_assistant(user, query: str, mode: str = "chat"):
    query = (query or "").strip()
    if not query:
        return False, "Please enter a health-related question."
    if len(query) > 2000:
        return False, "Your question is too long. Please shorten it."

    api_key = current_app.config.get("OPENROUTER_API_KEY")
    if not api_key:
        return False, NOT_CONFIGURED_MESSAGE

    mode_instruction = {
        "chat": "Answer the user's health question clearly.",
        "recommend": "Provide general, non-diagnostic health recommendations based only on the user's data.",
        "summary": (
            "Write a concise summary of the user's medicines and appointments only. "
            "Do not include their name, user ID, blood group, height, weight, allergies, "
            "chronic conditions, or other personal profile details. If there are no "
            "medicine or appointment records, say so briefly."
        ),
    }.get(mode, "Answer the user's health question clearly.")

    if mode == "summary":
        context = _relevant_context(user, "medicine appointment", include_health_record=False)
    else:
        context_query = query if mode == "chat" else "summary recommendation health record medicine appointment"
        context = _relevant_context(user, context_query)
    try:
        client = _ai_client()
        response = client.chat.completions.create(
            model=current_app.config.get("OPENROUTER_MODEL") or "openai/gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "system",
                    "content": f"{mode_instruction}\n{AI_RESPONSE_STYLE}\nCurrent user context:\n{context}",
                },
                {"role": "user", "content": query},
            ],
            temperature=0.4,
            max_tokens=700,
        )
        content = _clean_ai_response(response.choices[0].message.content)
        if not content:
            return False, UNAVAILABLE_MESSAGE
        return True, content
    except Exception as exc:
        message = _ai_error_message(exc)
        if message is UNAVAILABLE_MESSAGE:
            current_app.logger.exception("AI health assistant request failed")
        else:
            current_app.logger.warning("AI health assistant request failed: %s", exc)
        return False, message


def build_ai_pdf(text: str, user_name: str) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, title="HealthMate AI Response")
    styles = getSampleStyleSheet()
    safe = (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br/>")
    story = [
        Paragraph("HealthMate AI", styles["Title"]),
        Spacer(1, 0.15 * inch),
        Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles["Normal"]),
        Paragraph(f"User: {user_name}", styles["Normal"]),
        Spacer(1, 0.2 * inch),
        Paragraph(safe, styles["BodyText"]),
        Spacer(1, 0.3 * inch),
        Paragraph(
            "Disclaimer: This assistant provides general health information only. "
            "It is not a doctor and does not provide diagnosis or treatment. "
            "Seek professional medical help for serious concerns.",
            styles["Italic"],
        ),
    ]
    doc.build(story)
    return buffer.getvalue()


def build_ai_excel(text: str, user_name: str) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "AI Response"
    sheet.append(["HealthMate AI Assistant"])
    sheet.append(["User", user_name])
    sheet.append(["Generated", datetime.now().strftime("%Y-%m-%d %H:%M")])
    sheet.append([])
    sheet.append(["Response"])
    sheet.append([text])
    sheet["A1"].font = Font(bold=True, size=14)
    sheet["A5"].font = Font(bold=True)
    sheet["A6"].alignment = Alignment(wrap_text=True, vertical="top")
    sheet.column_dimensions["A"].width = 100
    sheet.column_dimensions["B"].width = 28
    sheet.row_dimensions[6].height = max(45, min(300, 15 * (text.count("\n") + 1)))
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def build_ai_image(text: str, user_name: str) -> bytes:
    from PIL import Image, ImageDraw, ImageFont

    font = ImageFont.load_default()
    title_font = ImageFont.load_default()
    lines = []
    for paragraph in text.splitlines() or [""]:
        while len(paragraph) > 88:
            split_at = paragraph.rfind(" ", 0, 88)
            split_at = split_at if split_at > 0 else 88
            lines.append(paragraph[:split_at])
            paragraph = paragraph[split_at:].lstrip()
        lines.append(paragraph)
    line_height = 18
    image = Image.new("RGB", (1200, max(260, 150 + line_height * len(lines))), "white")
    draw = ImageDraw.Draw(image)
    draw.text((50, 35), "HealthMate AI Assistant", fill="#17324d", font=title_font)
    draw.text((50, 70), f"User: {user_name}  |  Generated: {datetime.now():%Y-%m-%d %H:%M}", fill="#52606d", font=font)
    y = 125
    for line in lines:
        draw.text((50, y), line, fill="#17202a", font=font)
        y += line_height
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()

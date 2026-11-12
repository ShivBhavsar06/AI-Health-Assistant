from datetime import datetime, timedelta

from models.reminder import Reminder
from extensions import db
from utils.id_generator import PREFIXES, assign_new_id


def _slot_times(medicine):
    return [
        medicine.morning_time,
        medicine.afternoon_time,
        medicine.evening_time,
        medicine.night_time,
    ]


def sync_medicine_reminders(medicine):
    Reminder.query.filter_by(medicine_id=medicine.medicine_id, reminder_type="Medicine", status="Pending").delete()
    db.session.flush()
    if not medicine.start_date:
        return
    end = medicine.end_date or medicine.start_date
    if end < medicine.start_date:
        end = medicine.start_date
    if (end - medicine.start_date).days > 120:
        end = medicine.start_date + timedelta(days=120)
    current = medicine.start_date
    while current <= end:
        for slot in _slot_times(medicine):
            if slot:
                reminder = Reminder(
                    medicine_id=medicine.medicine_id,
                    appointment_id=None,
                    reminder_type="Medicine",
                    reminder_date=current,
                    reminder_time=slot,
                    status="Pending",
                )
                assign_new_id(reminder, PREFIXES["reminder"], "reminder_id")
                db.session.add(reminder)
        current += timedelta(days=1)


def sync_appointment_reminder(appointment):
    Reminder.query.filter_by(
        appointment_id=appointment.appointment_id, reminder_type="Appointment", status="Pending"
    ).delete()
    db.session.flush()
    if not appointment.appointment_date or not appointment.appointment_time:
        return
    if appointment.status == "Cancelled":
        return
    reminder = Reminder(
        medicine_id=None,
        appointment_id=appointment.appointment_id,
        reminder_type="Appointment",
        reminder_date=appointment.appointment_date,
        reminder_time=appointment.appointment_time,
        status="Pending" if appointment.status != "Completed" else "Completed",
    )
    assign_new_id(reminder, PREFIXES["reminder"], "reminder_id")
    db.session.add(reminder)


def reminder_datetime(reminder):
    if reminder.reminder_date is None or reminder.reminder_time is None:
        return None
    return datetime.combine(reminder.reminder_date, reminder.reminder_time)


def refresh_missed_reminders(reminders, grace_minutes=30):
    now = datetime.now()
    cutoff = now - timedelta(minutes=grace_minutes)
    for reminder in reminders:
        if reminder.status != "Pending":
            continue
        when = reminder_datetime(reminder)
        if when and when < cutoff:
            reminder.status = "Missed"
    return reminders


def due_reminder_payloads(reminders, ahead_minutes=0, behind_minutes=1):
    now = datetime.now()
    start = now - timedelta(minutes=behind_minutes)
    end = now + timedelta(minutes=ahead_minutes)
    payloads = []
    for reminder in reminders:
        if reminder.status != "Pending":
            continue
        when = reminder_datetime(reminder)
        if not when or when < start or when > end:
            continue
        payloads.append(serialize_reminder(reminder, when, now))
    payloads.sort(key=lambda item: item["when"])
    return payloads


def serialize_reminder(reminder, when=None, now=None):
    when = when or reminder_datetime(reminder)
    now = now or datetime.now()
    title = f"{reminder.reminder_type} reminder"
    detail = ""
    extra = ""
    if reminder.reminder_type == "Medicine" and reminder.medicine:
        title = f"Time to take {reminder.medicine.medicine_name}"
        extra = reminder.medicine.medicine_name
        detail = reminder.medicine.dosage or reminder.medicine.instructions or "Medicine dose reminder"
    elif reminder.reminder_type == "Appointment" and reminder.appointment:
        doctor = reminder.appointment.doctor_name or "your doctor"
        title = f"Appointment with {doctor}"
        extra = reminder.appointment.hospital_name or reminder.appointment.purpose or ""
        detail = extra or "Upcoming appointment reminder"
    seconds = (when - now).total_seconds() if when else 0
    return {
        "id": reminder.reminder_id,
        "type": reminder.reminder_type,
        "title": title,
        "detail": detail,
        "name": extra,
        "date": reminder.reminder_date.isoformat() if reminder.reminder_date else "",
        "time": reminder.reminder_time.strftime("%H:%M") if reminder.reminder_time else "",
        "when": when.isoformat(timespec="minutes") if when else "",
        "soon": seconds > 0,
        "complete_url": f"/reminders/{reminder.reminder_id}/complete",
    }


def reminder_belongs_to_user(reminder, user_id: str) -> bool:
    if reminder.reminder_type == "Medicine" and reminder.medicine:
        return reminder.medicine.user_id == user_id
    if reminder.reminder_type == "Appointment" and reminder.appointment:
        return reminder.appointment.user_id == user_id
    return False

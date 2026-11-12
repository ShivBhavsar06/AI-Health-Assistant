from extensions import db


class Reminder(db.Model):
    __tablename__ = "reminders"

    reminder_id = db.Column(db.String(20), primary_key=True)
    medicine_id = db.Column(db.String(20), db.ForeignKey("medicines.medicine_id", ondelete="CASCADE"), nullable=True)
    appointment_id = db.Column(
        db.String(20), db.ForeignKey("appointments.appointment_id", ondelete="CASCADE"), nullable=True
    )
    reminder_type = db.Column(db.Enum("Medicine", "Appointment"), nullable=False)
    reminder_date = db.Column(db.Date)
    reminder_time = db.Column(db.Time)
    status = db.Column(db.Enum("Pending", "Completed", "Missed"), nullable=False, default="Pending")

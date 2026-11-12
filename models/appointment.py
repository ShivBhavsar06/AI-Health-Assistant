from extensions import db


class Appointment(db.Model):
    __tablename__ = "appointments"

    appointment_id = db.Column(db.String(20), primary_key=True)
    user_id = db.Column(db.String(20), db.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    doctor_name = db.Column(db.String(100), nullable=False)
    hospital_name = db.Column(db.String(150))
    appointment_date = db.Column(db.Date, nullable=False)
    appointment_time = db.Column(db.Time, nullable=False)
    purpose = db.Column(db.Text)
    status = db.Column(db.Enum("Upcoming", "Completed", "Cancelled"), default="Upcoming")

    reminders = db.relationship("Reminder", backref="appointment", cascade="all, delete-orphan")

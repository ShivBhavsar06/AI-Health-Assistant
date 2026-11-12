from datetime import datetime

from extensions import db


class Medicine(db.Model):
    __tablename__ = "medicines"

    medicine_id = db.Column(db.String(20), primary_key=True)
    user_id = db.Column(db.String(20), db.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    medicine_name = db.Column(db.String(150), nullable=False)
    dosage = db.Column(db.String(100))
    morning_time = db.Column(db.Time)
    afternoon_time = db.Column(db.Time)
    evening_time = db.Column(db.Time)
    night_time = db.Column(db.Time)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    instructions = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    reminders = db.relationship("Reminder", backref="medicine", cascade="all, delete-orphan")

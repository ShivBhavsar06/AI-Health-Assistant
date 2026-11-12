from datetime import datetime

from extensions import db


class HealthRecord(db.Model):
    __tablename__ = "health_records"

    record_id = db.Column(db.String(20), primary_key=True)
    user_id = db.Column(db.String(20), db.ForeignKey("users.user_id", ondelete="CASCADE"), unique=True, nullable=False)
    blood_group = db.Column(db.String(10))
    height = db.Column(db.Numeric(5, 2))
    weight = db.Column(db.Numeric(5, 2))
    allergies = db.Column(db.Text)
    chronic_disease = db.Column(db.Text)
    smoking_status = db.Column(db.String(30))
    alcohol_use = db.Column(db.String(30))
    exercise_habits = db.Column(db.Text)
    diet = db.Column(db.Text)
    other_lifestyle = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

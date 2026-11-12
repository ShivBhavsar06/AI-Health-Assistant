from datetime import datetime

from extensions import db


class MedicalReport(db.Model):
    __tablename__ = "medical_reports"

    report_id = db.Column(db.String(20), primary_key=True)
    user_id = db.Column(db.String(20), db.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    report_name = db.Column(db.String(150), nullable=False)
    report_type = db.Column(db.String(100))
    description = db.Column(db.Text)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    file_path = db.Column(db.String(255))

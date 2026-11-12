from datetime import datetime

from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db

class User(db.Model):
    __tablename__ = "users"

    user_id = db.Column(db.String(20), primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False)
    phone_number = db.Column(db.String(15))
    date_of_birth = db.Column(db.Date)
    gender = db.Column(db.Enum("Male", "Female", "Other"))
    profile_photo = db.Column(db.String(255))
    emergency_contact_name = db.Column(db.String(100))
    emergency_contact_relationship = db.Column(db.String(50))
    emergency_contact_phone = db.Column(db.String(15))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    medicines = db.relationship("Medicine", backref="user", cascade="all, delete-orphan")
    appointments = db.relationship("Appointment", backref="user", cascade="all, delete-orphan")
    health_record = db.relationship("HealthRecord", backref="user", uselist=False, cascade="all, delete-orphan")
    medical_reports = db.relationship("MedicalReport", backref="user", cascade="all, delete-orphan")
    feedback_entries = db.relationship("Feedback", backref="user", cascade="all, delete-orphan")

    def set_password(self, raw_password: str) -> None:
        self.password = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password, raw_password)

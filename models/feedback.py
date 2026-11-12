from datetime import datetime

from extensions import db


class Feedback(db.Model):
    __tablename__ = "feedback"
    __table_args__ = (db.CheckConstraint("rating >= 1 AND rating <= 5", name="feedback_rating_range"),)

    feedback_id = db.Column(db.String(20), primary_key=True)
    user_id = db.Column(db.String(20), db.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    rating = db.Column(db.Numeric(2, 1), nullable=False)
    comments = db.Column(db.Text)
    feedback_date = db.Column(db.DateTime, default=datetime.utcnow)

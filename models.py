"""
Database models (SQLAlchemy ORM) — persistent storage backed by SQLite.
"""
from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


def _now():
    return datetime.now(timezone.utc)


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=_now)

    assessments = db.relationship("Assessment", backref="user", lazy=True)

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)


class Assessment(db.Model):
    __tablename__ = "assessments"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    # Inputs: mission + habitat profile
    mission_name = db.Column(db.String(100), nullable=False, default="Unnamed mission")
    crew_size = db.Column(db.Integer, nullable=False)
    mission_days = db.Column(db.Integer, nullable=False)
    food_days_stock = db.Column(db.Integer, nullable=False)
    water_recycling_percent = db.Column(db.Float, nullable=False)
    oxygen_system = db.Column(db.String(20), nullable=False)
    radiation_shielding = db.Column(db.String(20), nullable=False)
    power_source = db.Column(db.String(20), nullable=False)
    medical_officer = db.Column(db.Boolean, nullable=False, default=False)
    backup_habitat = db.Column(db.Boolean, nullable=False, default=False)

    # Computed results
    food_ratio = db.Column(db.Float, nullable=False)
    risk_score = db.Column(db.Float, nullable=False)
    risk_category = db.Column(db.String(20), nullable=False)
    survival_probability = db.Column(db.Float, nullable=False)
    predicted_survival_days = db.Column(db.Float, nullable=False)

    created_at = db.Column(db.DateTime, default=_now)


class Feedback(db.Model):
    """Quick user feedback about the whole assessment process."""
    __tablename__ = "feedback"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    assessment_id = db.Column(db.Integer, db.ForeignKey("assessments.id"), nullable=True)
    rating = db.Column(db.Integer, nullable=False)
    helpful = db.Column(db.String(10), nullable=False)
    comment = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=_now)

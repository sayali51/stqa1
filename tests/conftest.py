"""
Shared pytest fixtures — a fresh Flask app with an isolated in-memory
SQLite database for every single test.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

import pytest
from app import create_app
from models import db


@pytest.fixture
def app():
    application = create_app({
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "TESTING": True,
    })
    yield application
    with application.app_context():
        db.session.remove()
        db.drop_all()
        db.engine.dispose()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def registered_client(client):
    """A client that has already registered and logged in as a test user."""
    client.post("/register", data={"name": "Sayali", "email": "sayali@test.com", "password": "pass123"})
    client.post("/login", data={"email": "sayali@test.com", "password": "pass123"})
    return client


def second_user_client(app, email="b@test.com"):
    other = app.test_client()
    other.post("/register", data={"name": "B", "email": email, "password": "pass123"})
    other.post("/login", data={"email": email, "password": "pass123"})
    return other


# A comfortable, well-prepared mission: food 1.2x (+3), water 80% (+4), stored O2 (+8),
# partial shield (+8), solar+battery (+5), medical yes, backup yes, crew 6  => score 28 (Moderate)
VALID_ASSESSMENT_FORM = {
    "mission_name": "Test Base", "crew_size": "6", "mission_days": "500", "food_days_stock": "600",
    "water_recycling_percent": "80", "oxygen_system": "stored", "radiation_shielding": "partial",
    "power_source": "solar_battery", "medical_officer": "yes", "backup_habitat": "yes",
}

# Best case: every factor optimal => score 0
IDEAL_FORM = dict(VALID_ASSESSMENT_FORM, food_days_stock="800", water_recycling_percent="95",
                  oxygen_system="isru", radiation_shielding="regolith", power_source="nuclear")

# Worst case: every factor worst => raw 107, clamped to 100
WORST_FORM = dict(VALID_ASSESSMENT_FORM, crew_size="2", food_days_stock="0", water_recycling_percent="0",
                  oxygen_system="limited", radiation_shielding="minimal", power_source="solar_only",
                  medical_officer="no", backup_habitat="no")

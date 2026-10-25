"""
INTEGRATION TESTS: auth + business logic + database working together.
Tool: pytest + Flask test client + real (in-memory) SQLite.
"""
import re
from models import db, User, Assessment
import business_logic as bl
from conftest import VALID_ASSESSMENT_FORM, WORST_FORM, second_user_client


def test_registration_persists_with_hashed_password(client, app):
    client.post("/register", data={"name": "A", "email": "a@x.com", "password": "secret1"})
    with app.app_context():
        u = User.query.filter_by(email="a@x.com").one()
        assert u.password_hash != "secret1" and u.check_password("secret1") and not u.check_password("nope")


def test_assessment_persisted_with_computed_values(registered_client, app):
    registered_client.post("/assessment/new", data=VALID_ASSESSMENT_FORM)
    with app.app_context():
        a = Assessment.query.one()
        expected = bl.compute_assessment(6, 500, 600, 80, "stored", "partial", "solar_battery", True, True)
        assert (a.risk_score, a.risk_category, a.survival_probability, a.predicted_survival_days) == (
            expected["risk_score"], expected["risk_category"], expected["survival_probability"],
            expected["predicted_survival_days"])
        assert a.mission_name == "Test Base" and a.user.email == "sayali@test.com"


def test_invalid_assessment_not_persisted(registered_client, app):
    registered_client.post("/assessment/new", data=dict(VALID_ASSESSMENT_FORM, crew_size="0"))
    with app.app_context():
        assert Assessment.query.count() == 0


def test_history_lists_only_own_assessments(app, registered_client):
    registered_client.post("/assessment/new", data=VALID_ASSESSMENT_FORM)
    registered_client.post("/assessment/new", data=WORST_FORM)
    other = second_user_client(app)
    other.post("/assessment/new", data=dict(VALID_ASSESSMENT_FORM, mission_name="Other Base"))
    mine = registered_client.get("/history").text
    assert len(re.findall(r'href="/assessment/\d+"', mine)) == 2 and "Other Base" not in mine
    assert len(re.findall(r'href="/assessment/\d+"', other.get("/history").text)) == 1

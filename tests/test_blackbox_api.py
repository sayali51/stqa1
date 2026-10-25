"""
BLACK-BOX TESTS through real HTTP requests (Flask test client)
Technique : Equivalence Class Partitioning + Boundary Value Analysis,
            input validation, authentication and access control.
"""
import pytest
from conftest import VALID_ASSESSMENT_FORM, IDEAL_FORM, WORST_FORM


# ---------------------------- pages & auth ----------------------------
def test_index_redirects_to_login_when_logged_out(client):
    r = client.get("/")
    assert r.status_code == 302 and "/login" in r.headers["Location"]

def test_index_redirects_to_assessment_when_logged_in(registered_client):
    r = registered_client.get("/")
    assert r.status_code == 302 and "/assessment/new" in r.headers["Location"]

def test_register_page_loads(client):
    assert client.get("/register").status_code == 200

def test_login_page_loads(client):
    assert b"Login" in client.get("/login").data

def test_register_success(client):
    r = client.post("/register", data={"name": "A", "email": "a@x.com", "password": "secret1"}, follow_redirects=True)
    assert b"Registration successful" in r.data

@pytest.mark.parametrize("data,msg", [
    ({"name": "", "email": "a@x.com", "password": "secret1"}, b"required"),
    ({"name": "A", "email": "", "password": "secret1"}, b"required"),
    ({"name": "A", "email": "a@x.com", "password": ""}, b"required"),
    ({"name": "A", "email": "no-at-sign", "password": "secret1"}, b"valid email"),
    ({"name": "A", "email": "a@x.com", "password": "12345"}, b"at least 6"),
])
def test_register_validation(client, data, msg):
    assert msg in client.post("/register", data=data).data

def test_register_password_boundary_6_accepted(client):
    r = client.post("/register", data={"name": "A", "email": "a@x.com", "password": "123456"}, follow_redirects=True)
    assert b"Registration successful" in r.data

def test_register_duplicate_email(client):
    d = {"name": "A", "email": "a@x.com", "password": "secret1"}
    client.post("/register", data=d)
    assert b"already exists" in client.post("/register", data=d).data

def test_login_wrong_password(client):
    client.post("/register", data={"name": "A", "email": "a@x.com", "password": "secret1"})
    assert b"Invalid email or password" in client.post("/login", data={"email": "a@x.com", "password": "wrong"}).data

def test_login_unknown_user(client):
    assert b"Invalid email or password" in client.post("/login", data={"email": "x@x.com", "password": "secret1"}).data

def test_logout_clears_session(registered_client):
    registered_client.get("/logout")
    r = registered_client.get("/assessment/new")
    assert r.status_code == 302 and "/login" in r.headers["Location"]

@pytest.mark.parametrize("path", ["/assessment/new", "/history", "/assessment/1", "/feedback"])
def test_protected_pages_require_login(client, path):
    r = client.get(path)
    assert r.status_code == 302 and "/login" in r.headers["Location"]


# ----------------------- assessment: valid classes -----------------------
def test_form_page_loads(registered_client):
    assert b"Mars Mission Assessment" in registered_client.get("/assessment/new").data

def test_valid_assessment_shows_results(registered_client):
    r = registered_client.post("/assessment/new", data=VALID_ASSESSMENT_FORM, follow_redirects=True)
    assert b"Moderate Risk" in r.data and b"74.8%" in r.data and b"Test Base" in r.data

def test_ideal_mission_is_low_risk(registered_client):
    r = registered_client.post("/assessment/new", data=IDEAL_FORM, follow_redirects=True)
    assert b"Low Risk" in r.data and b"100.0%" in r.data

def test_worst_mission_is_high_risk_and_clamped(registered_client):
    r = registered_client.post("/assessment/new", data=WORST_FORM, follow_redirects=True)
    assert b"High Risk" in r.data and b"100 / 100" in r.data and b"10.0%" in r.data

def test_blank_mission_name_defaults(registered_client):
    r = registered_client.post("/assessment/new", data=dict(VALID_ASSESSMENT_FORM, mission_name="  "), follow_redirects=True)
    assert b"Unnamed mission" in r.data


# ------------------- assessment: invalid classes & BVA -------------------
@pytest.mark.parametrize("field,value", [
    ("crew_size", "abc"), ("mission_days", ""), ("food_days_stock", "1.5x"), ("water_recycling_percent", "high")])
def test_non_numeric_input_rejected(registered_client, field, value):
    r = registered_client.post("/assessment/new", data=dict(VALID_ASSESSMENT_FORM, **{field: value}))
    assert b"valid numeric values" in r.data

@pytest.mark.parametrize("field,value,msg", [
    ("crew_size", "0", b"crew_size"), ("crew_size", "101", b"crew_size"),
    ("mission_days", "0", b"mission_days"), ("mission_days", "1826", b"mission_days"),
    ("food_days_stock", "-1", b"food_days_stock"), ("food_days_stock", "5001", b"food_days_stock"),
    ("water_recycling_percent", "-0.1", b"water_recycling_percent"),
    ("water_recycling_percent", "100.1", b"water_recycling_percent"),
])
def test_boundary_just_outside_rejected(registered_client, field, value, msg):
    r = registered_client.post("/assessment/new", data=dict(VALID_ASSESSMENT_FORM, **{field: value}))
    assert msg in r.data

@pytest.mark.parametrize("field,value", [
    ("crew_size", "1"), ("crew_size", "100"), ("mission_days", "1"), ("mission_days", "1825"),
    ("food_days_stock", "0"), ("food_days_stock", "5000"),
    ("water_recycling_percent", "0"), ("water_recycling_percent", "100")])
def test_boundary_at_limit_accepted(registered_client, field, value):
    r = registered_client.post("/assessment/new", data=dict(VALID_ASSESSMENT_FORM, **{field: value}), follow_redirects=True)
    assert b"Results Dashboard" in r.data

@pytest.mark.parametrize("field", ["oxygen_system", "radiation_shielding", "power_source"])
def test_invalid_choice_rejected(registered_client, field):
    r = registered_client.post("/assessment/new", data=dict(VALID_ASSESSMENT_FORM, **{field: "bogus"}))
    assert field.encode() in r.data

def test_mission_name_too_long_rejected(registered_client):
    r = registered_client.post("/assessment/new", data=dict(VALID_ASSESSMENT_FORM, mission_name="x" * 101))
    assert b"at most 100" in r.data


# ----------------------------- access control -----------------------------
def test_nonexistent_assessment(registered_client):
    r = registered_client.get("/assessment/999", follow_redirects=True)
    assert b"Assessment not found" in r.data

def test_cross_user_access_denied(app, registered_client):
    registered_client.post("/assessment/new", data=VALID_ASSESSMENT_FORM)
    from conftest import second_user_client
    other = second_user_client(app)
    r = other.get("/assessment/1", follow_redirects=True)
    assert b"do not have access" in r.data and b"Test Base" not in r.data

def test_xss_in_mission_name_is_escaped(registered_client):
    r = registered_client.post("/assessment/new", data=dict(VALID_ASSESSMENT_FORM, mission_name="<script>alert(1)</script>"),
                               follow_redirects=True)
    assert b"<script>alert(1)</script>" not in r.data and b"&lt;script&gt;" in r.data

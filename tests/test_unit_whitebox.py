"""
UNIT TESTS (white-box) on business_logic.py
Technique : statement + branch coverage, boundary values on every threshold
Tool      : pytest
"""
import pytest
import business_logic as bl


# ---------------- food_coverage_ratio / food_risk_points ----------------
def test_food_ratio_basic():
    assert bl.food_coverage_ratio(600, 500) == 1.2

def test_food_ratio_zero_stock():
    assert bl.food_coverage_ratio(0, 100) == 0

@pytest.mark.parametrize("stock,days", [(10, 0), (10, -5)])
def test_food_ratio_rejects_non_positive_mission(stock, days):
    with pytest.raises(ValueError):
        bl.food_coverage_ratio(stock, days)

def test_food_ratio_rejects_negative_stock():
    with pytest.raises(ValueError):
        bl.food_coverage_ratio(-1, 100)

@pytest.mark.parametrize("ratio,expected", [
    (0, 20), (0.74, 20), (0.75, 10), (0.99, 10), (1.0, 3), (1.49, 3), (1.5, 0), (3.0, 0)])
def test_food_points_boundaries(ratio, expected):
    assert bl.food_risk_points(ratio) == expected


# ---------------- water ----------------
@pytest.mark.parametrize("pct,expected", [
    (0, 18), (49.9, 18), (50, 10), (69.9, 10), (70, 4), (89.9, 4), (90, 0), (100, 0)])
def test_water_points_boundaries(pct, expected):
    assert bl.water_risk_points(pct) == expected

@pytest.mark.parametrize("pct", [-0.1, 100.1])
def test_water_rejects_out_of_range(pct):
    with pytest.raises(ValueError):
        bl.water_risk_points(pct)


# ---------------- systems ----------------
@pytest.mark.parametrize("o2,expected", [("isru", 0), ("stored", 8), ("limited", 20)])
def test_oxygen_points(o2, expected):
    assert bl.systems_risk_points(o2, "regolith", "nuclear") == expected

@pytest.mark.parametrize("sh,expected", [("regolith", 0), ("partial", 8), ("minimal", 18)])
def test_shielding_points(sh, expected):
    assert bl.systems_risk_points("isru", sh, "nuclear") == expected

@pytest.mark.parametrize("pw,expected", [("nuclear", 0), ("solar_battery", 5), ("solar_only", 12)])
def test_power_points(pw, expected):
    assert bl.systems_risk_points("isru", "regolith", pw) == expected

@pytest.mark.parametrize("args", [("coal", "regolith", "nuclear"), ("isru", "none", "nuclear"), ("isru", "regolith", "wind")])
def test_systems_rejects_invalid_choice(args):
    with pytest.raises(ValueError):
        bl.systems_risk_points(*args)

def test_systems_worst_case_sum():
    assert bl.systems_risk_points("limited", "minimal", "solar_only") == 50


# ---------------- crew ----------------
def test_crew_all_good():
    assert bl.crew_risk_points(6, True, True) == 0

def test_crew_small_crew_boundary():
    assert bl.crew_risk_points(3, True, True) == 5
    assert bl.crew_risk_points(4, True, True) == 0

def test_crew_no_medical():
    assert bl.crew_risk_points(6, False, True) == 6

def test_crew_no_backup():
    assert bl.crew_risk_points(6, True, False) == 8

def test_crew_worst_case():
    assert bl.crew_risk_points(1, False, False) == 19


# ---------------- calculate_risk_score ----------------
def test_score_ideal_is_zero():
    assert bl.calculate_risk_score(6, 500, 800, 95, "isru", "regolith", "nuclear", True, True) == 0

def test_score_known_mix():
    assert bl.calculate_risk_score(6, 500, 400, 60, "stored", "partial", "solar_only", False, False) == 62

def test_score_clamped_at_100():
    # raw sum is 107, must be clamped
    assert bl.calculate_risk_score(1, 100, 0, 0, "limited", "minimal", "solar_only", False, False) == 100

def test_score_propagates_invalid_input():
    with pytest.raises(ValueError):
        bl.calculate_risk_score(6, 0, 10, 50, "isru", "regolith", "nuclear", True, True)


# ---------------- categorize_risk ----------------
@pytest.mark.parametrize("score,cat", [
    (0, "Low Risk"), (25, "Low Risk"), (26, "Moderate Risk"), (55, "Moderate Risk"),
    (56, "High Risk"), (100, "High Risk")])
def test_category_boundaries(score, cat):
    assert bl.categorize_risk(score) == cat

@pytest.mark.parametrize("score", [-1, 101])
def test_category_rejects_out_of_range(score):
    with pytest.raises(ValueError):
        bl.categorize_risk(score)


# ---------------- survival probability / days ----------------
@pytest.mark.parametrize("score,p", [(0, 100.0), (50, 55.0), (100, 10.0), (62, 44.2)])
def test_survival_probability_values(score, p):
    assert bl.survival_probability(score) == p

@pytest.mark.parametrize("score", [-1, 101])
def test_survival_probability_rejects_invalid(score):
    with pytest.raises(ValueError):
        bl.survival_probability(score)

def test_predicted_days_scale():
    assert bl.predicted_survival_days(500, 0) == 500.0
    assert bl.predicted_survival_days(500, 62) == 221.0

@pytest.mark.parametrize("days", [0, 1826])
def test_predicted_days_rejects_bad_mission_length(days):
    with pytest.raises(ValueError):
        bl.predicted_survival_days(days, 10)


# ---------------- validate_inputs ----------------
@pytest.mark.parametrize("crew,days,food,water", [
    (0, 100, 100, 50), (101, 100, 100, 50), (5, 0, 100, 50), (5, 1826, 100, 50),
    (5, 100, -1, 50), (5, 100, 5001, 50), (5, 100, 100, -1), (5, 100, 100, 101)])
def test_validate_inputs_rejects(crew, days, food, water):
    with pytest.raises(ValueError):
        bl.validate_inputs(crew, days, food, water)

@pytest.mark.parametrize("crew,days,food,water", [(1, 1, 0, 0), (100, 1825, 5000, 100)])
def test_validate_inputs_accepts_boundaries(crew, days, food, water):
    bl.validate_inputs(crew, days, food, water)   # must not raise


# ---------------- compute_assessment ----------------
def test_compute_assessment_keys_and_values():
    r = bl.compute_assessment(6, 500, 600, 80, "stored", "partial", "solar_battery", True, True)
    assert r == {"food_ratio": 1.2, "risk_score": 28, "risk_category": "Moderate Risk",
                 "survival_probability": 74.8, "predicted_survival_days": 374.0}

def test_compute_assessment_rejects_invalid_crew():
    with pytest.raises(ValueError):
        bl.compute_assessment(0, 500, 600, 80, "stored", "partial", "solar_battery", True, True)

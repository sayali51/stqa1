"""
Tests for the enhanced features: factor breakdown, tailored advice,
what-if simulator, SVG charts, and the feedback module.
Mix of white-box (unit), black-box (HTTP) and integration (DB) tests.
"""
import pytest
import business_logic as bl
import charts
from models import Feedback
from conftest import VALID_ASSESSMENT_FORM, IDEAL_FORM, WORST_FORM, second_user_client

# positional argument sets: (crew, days, food, water, o2, shield, power, medical, backup)
IDEAL = (6, 500, 800, 95, "isru", "regolith", "nuclear", True, True)
MIXED = (6, 500, 400, 60, "stored", "partial", "solar_only", False, False)   # score 62
WORST = (2, 500, 0, 0, "limited", "minimal", "solar_only", False, False)


# ------------------------- white-box: breakdown -------------------------
class TestRiskBreakdown:
    @pytest.mark.parametrize("args", [IDEAL, MIXED, WORST])
    def test_breakdown_sum_matches_score_unless_clamped(self, args):
        total = sum(f["points"] for f in bl.risk_breakdown(*args))
        assert max(0, min(100, total)) == bl.calculate_risk_score(*args)

    def test_ideal_breakdown_all_zero(self):
        assert all(f["points"] == 0 for f in bl.risk_breakdown(*IDEAL))

    def test_worst_breakdown_raw_sum_exceeds_100(self):
        assert sum(f["points"] for f in bl.risk_breakdown(*WORST)) == 107

    def test_breakdown_labels_present(self):
        assert [f["key"] for f in bl.risk_breakdown(*MIXED)] == [
            "food", "water", "oxygen", "shielding", "power", "medical", "backup", "crew"]

    def test_crew_factor_not_modifiable(self):
        mod = {f["key"]: f["modifiable"] for f in bl.risk_breakdown(*WORST)}
        assert mod["crew"] is False and mod["food"] is True

    def test_breakdown_rejects_invalid_system(self):
        with pytest.raises(ValueError):
            bl.risk_breakdown(6, 500, 800, 95, "coal", "regolith", "nuclear", True, True)


# ------------------------- white-box: recommendations -------------------------
class TestRecommendations:
    def test_unknown_category_rejected(self):
        with pytest.raises(ValueError):
            bl.get_recommendations("Extreme", *IDEAL)

    def test_ideal_gets_maintenance_advice(self):
        r = bl.get_recommendations("Low Risk", *IDEAL)
        assert [i["title"] for i in r["items"]] == ["Maintain your redundancy"]

    def test_items_sorted_by_priority(self):
        r = bl.get_recommendations("High Risk", *WORST)
        order = {"high": 0, "medium": 1, "low": 2}
        pr = [order[i["priority"]] for i in r["items"]]
        assert pr == sorted(pr)

    def test_worst_has_every_high_priority_item(self):
        titles = [i["title"] for i in bl.get_recommendations("High Risk", *WORST)["items"]]
        for t in ["Stock far more food", "Upgrade water recycling", "Add in-situ oxygen production",
                  "Improve radiation shielding", "Add a dust-storm-proof power source"]:
            assert t in titles

    @pytest.mark.parametrize("food,title", [
        (100, "Stock far more food"), (400, "Increase food reserves"), (600, "Add a food safety margin")])
    def test_food_advice_tiers(self, food, title):
        t = [i["title"] for i in bl.get_recommendations("Moderate Risk", 6, 500, food, 95, "isru", "regolith", "nuclear", True, True)["items"]]
        assert t == [title]

    @pytest.mark.parametrize("water,title", [
        (40, "Upgrade water recycling"), (60, "Improve water recycling"), (80, "Push water recycling to 90%+")])
    def test_water_advice_tiers(self, water, title):
        t = [i["title"] for i in bl.get_recommendations("Moderate Risk", 6, 500, 800, water, "isru", "regolith", "nuclear", True, True)["items"]]
        assert t == [title]

    def test_stored_oxygen_partial_shield_solar_battery_tips(self):
        t = [i["title"] for i in bl.get_recommendations("Moderate Risk", 6, 500, 800, 95, "stored", "partial", "solar_battery", True, True)["items"]]
        assert set(t) == {"Move from stored to produced oxygen", "Complete the radiation shielding", "Consider nuclear backup power"}

    def test_small_crew_tip(self):
        t = [i["title"] for i in bl.get_recommendations("Low Risk", 2, 500, 800, 95, "isru", "regolith", "nuclear", True, True)["items"]]
        assert t == ["Consider a larger crew"]

    def test_medical_and_backup_tips(self):
        t = [i["title"] for i in bl.get_recommendations("Low Risk", 6, 500, 800, 95, "isru", "regolith", "nuclear", False, False)["items"]]
        assert set(t) == {"Include a trained medical officer", "Build a backup habitat module"}

    def test_headline_changes_with_category(self):
        heads = {c: bl.get_recommendations(c, *IDEAL)["headline"] for c in ("Low Risk", "Moderate Risk", "High Risk")}
        assert len(set(heads.values())) == 3 and "high-risk" in heads["High Risk"]


# ------------------------- white-box: what-if -------------------------
class TestWhatIf:
    def test_no_scenarios_for_ideal(self):
        assert bl.what_if_scenarios(*IDEAL) == []

    def test_single_change_has_no_combined(self):
        s = bl.what_if_scenarios(6, 500, 800, 95, "isru", "regolith", "nuclear", False, True)
        assert [x["label"] for x in s] == ["Add medical officer"]
        assert s[0]["score_change"] == -6 and s[0]["new_score"] == 0

    def test_all_changes_scenario_is_best_and_low(self):
        s = bl.what_if_scenarios(*MIXED)
        assert s[-1]["label"] == "All upgrades together" and s[-1]["new_category"] == "Low Risk"
        assert s[-1]["new_score"] == min(x["new_score"] for x in s)

    def test_scenario_count_for_mixed(self):
        assert len(bl.what_if_scenarios(*MIXED)) == 8   # 7 single + combined

    def test_days_gained_matches_difference(self):
        base = bl.predicted_survival_days(500, 62)
        for s in bl.what_if_scenarios(*MIXED):
            assert s["days_gained"] == round(s["new_days"] - base, 1)

    def test_food_scenario_targets_1_5x(self):
        s = bl.what_if_scenarios(6, 501, 0, 95, "isru", "regolith", "nuclear", True, True)[0]
        assert s["label"] == "Stock 1.5x food" and s["new_score"] == 0   # ceil(501*1.5) = 752 stock

    def test_water_85_improves_to_95(self):
        labels = [x["label"] for x in bl.what_if_scenarios(6, 500, 800, 85, "isru", "regolith", "nuclear", True, True)]
        assert labels == ["Recycle 95% of water"]


# ------------------------- white-box: feedback validation -------------------------
class TestValidateFeedback:
    def test_valid_feedback_cleaned(self):
        assert bl.validate_feedback("4", "yes", "  nice  ") == (4, "yes", "nice")

    @pytest.mark.parametrize("rating", ["0", "6", "-1", "abc", "", None])
    def test_invalid_rating_rejected(self, rating):
        with pytest.raises(ValueError):
            bl.validate_feedback(rating, "yes", "")

    @pytest.mark.parametrize("rating", [1, 5])
    def test_rating_boundaries_accepted(self, rating):
        assert bl.validate_feedback(rating, "no", "")[0] == rating

    def test_invalid_helpful_rejected(self):
        with pytest.raises(ValueError):
            bl.validate_feedback(3, "maybe", "")

    def test_comment_length_boundary(self):
        assert len(bl.validate_feedback(3, "yes", "x" * 500)[2]) == 500
        with pytest.raises(ValueError):
            bl.validate_feedback(3, "yes", "x" * 501)

    def test_none_comment_becomes_empty(self):
        assert bl.validate_feedback(3, "yes", None)[2] == ""


# ------------------------- white-box: charts -------------------------
class TestCharts:
    def test_gauge_content(self):
        svg = charts.risk_gauge(62, "High Risk")
        assert "<svg" in svg and "62 / 100" in svg and "High Risk" in svg

    def test_gauge_clamps(self):
        assert "100 / 100" in charts.risk_gauge(250, "High Risk")
        assert "0 / 100" in charts.risk_gauge(-5, "Low Risk")

    def test_gauge_escapes_category(self):
        assert "<script>" not in charts.risk_gauge(10, "<script>alert(1)</script>")

    def test_factor_chart_values_and_zero_bar(self):
        svg = charts.factor_bar_chart(bl.risk_breakdown(*MIXED))
        assert "+12" in svg and ">0<" in svg

    def test_factor_chart_negative_points(self):
        assert "-5" in charts.factor_bar_chart([{"label": "X", "points": -5}])

    def test_survival_comparison_values(self):
        svg = charts.survival_comparison_chart(500, 221.0)
        assert "500 days" in svg and "221 days" in svg

    def test_survival_comparison_zero(self):
        assert "0 days" in charts.survival_comparison_chart(100, 0)

    @pytest.mark.parametrize("p,color", [(90, "#2e8b57"), (60, "#d98e04"), (20, "#c0392b")])
    def test_probability_meter_color_bands(self, p, color):
        assert color in charts.probability_meter(p)

    def test_probability_meter_clamps(self):
        assert "100.0%" in charts.probability_meter(500) and "0.0%" in charts.probability_meter(-9)

    def test_what_if_chart(self):
        svg = charts.what_if_chart(62, bl.what_if_scenarios(*MIXED))
        assert "Current" in svg and "Add nuclear power" in svg

    def test_trend_empty(self):
        assert "No assessments yet" in charts.trend_chart([])

    def test_trend_single_point_no_line(self):
        svg = charts.trend_chart([30])
        assert "<polyline" not in svg and "<circle" in svg

    def test_trend_multiple_points(self):
        svg = charts.trend_chart([10, 30, 55])
        assert "<polyline" in svg and svg.count("<circle") == 3


# ------------------------- black-box: dashboard -------------------------
class TestResultDashboard:
    def test_dashboard_sections(self, registered_client):
        t = registered_client.post("/assessment/new", data=WORST_FORM, follow_redirects=True).text
        assert t.count("<svg") >= 5
        for s in ["Personalised advice", "What if you upgraded something?", "Quick feedback",
                  "Planned mission vs predicted survivable days", "Stock far more food"]:
            assert s in t

    def test_ideal_mission_shows_maintenance_and_no_upgrades(self, registered_client):
        t = registered_client.post("/assessment/new", data=IDEAL_FORM, follow_redirects=True).text
        assert "Maintain your redundancy" in t and "already in place" in t

    def test_advice_differs_by_risk_level(self, registered_client):
        hi = registered_client.post("/assessment/new", data=WORST_FORM, follow_redirects=True).text
        lo = registered_client.post("/assessment/new", data=IDEAL_FORM, follow_redirects=True).text
        assert "high-risk band" in hi and "low-risk band" in lo

    def test_inputs_table_uses_readable_labels(self, registered_client):
        t = registered_client.post("/assessment/new", data=VALID_ASSESSMENT_FORM, follow_redirects=True).text
        assert "Stored oxygen tanks" in t and "Partial shielding" in t

    def test_history_trend(self, registered_client):
        registered_client.post("/assessment/new", data=IDEAL_FORM)
        registered_client.post("/assessment/new", data=WORST_FORM)
        t = registered_client.get("/history").text
        assert "Risk score trend" in t and "<polyline" in t

    def test_history_empty_no_trend(self, registered_client):
        t = registered_client.get("/history").text
        assert "Risk score trend" not in t and "No assessments yet" in t


# ------------------------- black-box: feedback routes -------------------------
class TestFeedbackRoutes:
    def test_feedback_requires_login_post(self, client):
        assert client.post("/feedback", data={"rating": "5", "helpful": "yes"}).status_code == 302

    def test_feedback_page_renders(self, registered_client):
        t = registered_client.get("/feedback").text
        assert "Share your feedback" in t and "haven't submitted any feedback" in t

    def test_submit_valid_feedback(self, registered_client):
        r = registered_client.post("/feedback", data={"rating": "5", "helpful": "yes", "comment": "Great"}, follow_redirects=True)
        assert "Thank you" in r.text and "Great" in r.text and "5/5" in r.text

    @pytest.mark.parametrize("data,msg", [
        ({"helpful": "yes"}, "star rating"),
        ({"rating": "6", "helpful": "yes"}, "between 1 and 5"),
        ({"rating": "3", "helpful": ""}, "helpful"),
        ({"rating": "3", "helpful": "yes", "comment": "x" * 501}, "at most 500"),
    ])
    def test_invalid_feedback_rejected(self, registered_client, data, msg):
        r = registered_client.post("/feedback", data=data, follow_redirects=True)
        assert msg in r.text and "Thank you" not in r.text

    def test_invalid_feedback_keeps_assessment_link(self, registered_client):
        registered_client.post("/assessment/new", data=VALID_ASSESSMENT_FORM)
        r = registered_client.post("/feedback", data={"rating": "9", "helpful": "yes", "assessment_id": "1"})
        assert r.status_code == 302 and "assessment_id=1" in r.headers["Location"]

    def test_feedback_for_missing_assessment_rejected(self, registered_client):
        assert "Invalid assessment" in registered_client.get("/feedback?assessment_id=999", follow_redirects=True).text


# ------------------------- integration: feedback + DB -------------------------
class TestFeedbackIntegration:
    def test_persisted_and_linked(self, app, registered_client):
        registered_client.post("/assessment/new", data=VALID_ASSESSMENT_FORM)
        registered_client.post("/feedback", data={"rating": "4", "helpful": "somewhat", "comment": "ok", "assessment_id": "1"})
        with app.app_context():
            f = Feedback.query.one()
            assert (f.rating, f.helpful, f.comment, f.assessment_id) == (4, "somewhat", "ok", 1)

    def test_general_feedback_has_no_assessment(self, app, registered_client):
        registered_client.post("/feedback", data={"rating": "3", "helpful": "no"})
        with app.app_context():
            assert Feedback.query.one().assessment_id is None

    def test_cannot_attach_to_other_users_assessment(self, app, registered_client):
        registered_client.post("/assessment/new", data=VALID_ASSESSMENT_FORM)
        other = second_user_client(app)
        r = other.post("/feedback", data={"rating": "5", "helpful": "yes", "assessment_id": "1"}, follow_redirects=True)
        assert "Invalid assessment" in r.text
        with app.app_context():
            assert Feedback.query.count() == 0

    def test_users_only_see_own_feedback(self, app, registered_client):
        registered_client.post("/feedback", data={"rating": "5", "helpful": "yes", "comment": "secret-note"})
        assert "secret-note" not in second_user_client(app).get("/feedback").text

    def test_comment_html_escaped(self, registered_client):
        registered_client.post("/feedback", data={"rating": "5", "helpful": "yes", "comment": "<script>alert(1)</script>"})
        t = registered_client.get("/feedback").text
        assert "<script>alert(1)</script>" not in t and "&lt;script&gt;" in t

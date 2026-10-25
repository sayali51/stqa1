"""
Mars Colony Survival & Habitability Estimator
(OOMD/OOAD case study: "Mars Life Prediction / Habitat Survival System" —
implemented as an educational, rule-based estimator for an STQA mini-project.
See business_logic.py for the academic disclaimer.)

- Persistent SQLite database (via SQLAlchemy)
- Hashed passwords, session-based authentication
- Server-rendered HTML pages (Jinja2) with inline-SVG charts
- Application factory (create_app) so tests use an isolated in-memory DB
"""
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash

from models import db, User, Assessment, Feedback
from business_logic import (compute_assessment, risk_breakdown, get_recommendations,
                            what_if_scenarios, validate_feedback, LABELS)
import charts


def create_app(test_config=None):
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "dev-secret-key-change-in-production"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///mars_prediction.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    with app.app_context():
        db.create_all()

    app.jinja_env.globals["LABELS"] = LABELS

    def login_required(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            if "user_id" not in session:
                flash("Please log in to continue.", "error")
                return redirect(url_for("login"))
            return view_func(*args, **kwargs)
        return wrapped

    def factor_args(a):
        """Positional inputs shared by breakdown / advice / what-if functions."""
        return (a.crew_size, a.mission_days, a.food_days_stock, a.water_recycling_percent,
                a.oxygen_system, a.radiation_shielding, a.power_source,
                a.medical_officer, a.backup_habitat)

    # ---------------- routes ----------------
    @app.route("/")
    def index():
        if "user_id" in session:
            return redirect(url_for("new_assessment"))
        return redirect(url_for("login"))

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip()
            password = request.form.get("password", "").strip()

            if not name or not email or not password:
                flash("Name, email and password are all required.", "error")
                return render_template("register.html")
            if "@" not in email:
                flash("Please enter a valid email address.", "error")
                return render_template("register.html")
            if len(password) < 6:
                flash("Password must be at least 6 characters.", "error")
                return render_template("register.html")
            if User.query.filter_by(email=email).first() is not None:
                flash("An account with this email already exists.", "error")
                return render_template("register.html")

            user = User(name=name, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for("login"))
        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            email = request.form.get("email", "").strip()
            password = request.form.get("password", "").strip()
            user = User.query.filter_by(email=email).first()
            if user is not None and user.check_password(password):
                session["user_id"] = user.id
                session["user_name"] = user.name
                flash(f"Welcome back, {user.name}!", "success")
                return redirect(url_for("new_assessment"))
            flash("Invalid email or password.", "error")
            return render_template("login.html")
        return render_template("login.html")

    @app.route("/logout")
    def logout():
        session.clear()
        flash("You have been logged out.", "success")
        return redirect(url_for("login"))

    @app.route("/assessment/new", methods=["GET", "POST"])
    @login_required
    def new_assessment():
        if request.method == "POST":
            try:
                mission_name = request.form.get("mission_name", "").strip() or "Unnamed mission"
                crew_size = int(request.form.get("crew_size", ""))
                mission_days = int(request.form.get("mission_days", ""))
                food_days_stock = int(request.form.get("food_days_stock", ""))
                water_recycling_percent = float(request.form.get("water_recycling_percent", ""))
                oxygen_system = request.form.get("oxygen_system", "")
                radiation_shielding = request.form.get("radiation_shielding", "")
                power_source = request.form.get("power_source", "")
                medical_officer = request.form.get("medical_officer") == "yes"
                backup_habitat = request.form.get("backup_habitat") == "yes"
            except ValueError:
                flash("Please enter valid numeric values for crew size, mission days, food stock and water recycling.", "error")
                return render_template("assessment_form.html")

            if len(mission_name) > 100:
                flash("Mission name must be at most 100 characters.", "error")
                return render_template("assessment_form.html")

            try:
                result = compute_assessment(
                    crew_size, mission_days, food_days_stock, water_recycling_percent,
                    oxygen_system, radiation_shielding, power_source,
                    medical_officer, backup_habitat)
            except ValueError as e:
                flash(str(e), "error")
                return render_template("assessment_form.html")

            assessment = Assessment(
                user_id=session["user_id"], mission_name=mission_name, crew_size=crew_size,
                mission_days=mission_days, food_days_stock=food_days_stock,
                water_recycling_percent=water_recycling_percent, oxygen_system=oxygen_system,
                radiation_shielding=radiation_shielding, power_source=power_source,
                medical_officer=medical_officer, backup_habitat=backup_habitat,
                food_ratio=result["food_ratio"], risk_score=result["risk_score"],
                risk_category=result["risk_category"],
                survival_probability=result["survival_probability"],
                predicted_survival_days=result["predicted_survival_days"],
            )
            db.session.add(assessment)
            db.session.commit()
            flash("Assessment computed successfully.", "success")
            return redirect(url_for("assessment_detail", assessment_id=assessment.id))

        return render_template("assessment_form.html")

    @app.route("/assessment/<int:assessment_id>")
    @login_required
    def assessment_detail(assessment_id):
        a = db.session.get(Assessment, assessment_id)
        if a is None:
            flash("Assessment not found.", "error")
            return redirect(url_for("history"))
        if a.user_id != session["user_id"]:
            flash("You do not have access to this assessment.", "error")
            return redirect(url_for("history"))

        args = factor_args(a)
        breakdown = risk_breakdown(*args)
        advice = get_recommendations(a.risk_category, *args)
        scenarios = what_if_scenarios(*args)
        return render_template(
            "assessment_detail.html", a=a, breakdown=breakdown, advice=advice,
            scenarios=scenarios,
            gauge=charts.risk_gauge(a.risk_score, a.risk_category),
            meter=charts.probability_meter(a.survival_probability),
            factor_chart=charts.factor_bar_chart(breakdown),
            days_chart=charts.survival_comparison_chart(a.mission_days, a.predicted_survival_days),
            whatif_chart=charts.what_if_chart(a.risk_score, scenarios),
        )

    @app.route("/history")
    @login_required
    def history():
        assessments = Assessment.query.filter_by(
            user_id=session["user_id"]).order_by(Assessment.id.desc()).all()
        trend = charts.trend_chart([a.risk_score for a in reversed(assessments)])
        return render_template("history.html", assessments=assessments, trend=trend)

    @app.route("/feedback", methods=["GET", "POST"])
    @login_required
    def feedback():
        assessment_id = request.values.get("assessment_id", type=int)
        if assessment_id is not None:
            owned = db.session.get(Assessment, assessment_id)
            if owned is None or owned.user_id != session["user_id"]:
                flash("Invalid assessment for feedback.", "error")
                return redirect(url_for("feedback"))

        if request.method == "POST":
            try:
                rating, helpful, comment = validate_feedback(
                    request.form.get("rating"), request.form.get("helpful"),
                    request.form.get("comment"))
            except ValueError as e:
                flash(str(e), "error")
                if assessment_id:
                    return redirect(url_for("feedback", assessment_id=assessment_id))
                return redirect(url_for("feedback"))
            db.session.add(Feedback(user_id=session["user_id"], assessment_id=assessment_id,
                                    rating=rating, helpful=helpful, comment=comment))
            db.session.commit()
            flash("Thank you! Your feedback has been recorded.", "success")
            return redirect(url_for("feedback"))

        mine = Feedback.query.filter_by(user_id=session["user_id"]).order_by(Feedback.id.desc()).all()
        return render_template("feedback.html", assessment_id=assessment_id, past=mine)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=5000)

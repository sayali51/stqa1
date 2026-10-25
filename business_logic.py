"""
Pure business logic — no Flask, no database, no I/O.

IMPORTANT ACADEMIC DISCLAIMER:
This module implements a simplified, RULE-BASED, EDUCATIONAL estimation
model for a Software Testing & Quality Assurance mini-project (based on
the "Mars Life Prediction / Habitat Survival System" OOMD case study).
All coefficients are illustrative assumptions chosen to produce varied,
testable branches and boundary conditions. They are NOT derived from real
space-agency, engineering or life-support data and must never be used for
real mission planning. The purpose is to demonstrate white-box, black-box
and integration testing on a non-trivial piece of business logic.

Kept framework-free so it can be unit tested in complete isolation.
"""

# ---------------------------------------------------------------- constants
OXYGEN_SYSTEMS = ('isru', 'stored', 'limited')          # in-situ production / stored tanks / limited backup
SHIELDING_TYPES = ('regolith', 'partial', 'minimal')
POWER_SOURCES = ('nuclear', 'solar_battery', 'solar_only')

OXYGEN_POINTS = {'isru': 0, 'stored': 8, 'limited': 20}
SHIELDING_POINTS = {'regolith': 0, 'partial': 8, 'minimal': 18}
POWER_POINTS = {'nuclear': 0, 'solar_battery': 5, 'solar_only': 12}

LABELS = {
    'isru': 'In-situ oxygen production', 'stored': 'Stored oxygen tanks', 'limited': 'Limited backup oxygen',
    'regolith': 'Regolith / underground', 'partial': 'Partial shielding', 'minimal': 'Minimal shielding',
    'nuclear': 'Nuclear reactor', 'solar_battery': 'Solar + batteries', 'solar_only': 'Solar only',
}

MIN_CREW, MAX_CREW = 1, 100
MIN_MISSION_DAYS, MAX_MISSION_DAYS = 1, 1825
MAX_FOOD_DAYS = 5000
SMALL_CREW_LIMIT = 4            # crews below this get an isolation penalty

RISK_LOW_MAX = 25
RISK_MODERATE_MAX = 55
SURVIVAL_PENALTY_RATE = 0.9     # survival probability = 100 - score * 0.9
MIN_SURVIVAL_PERCENT = 0.0
NEUTRAL_FOOD_RATIO = 1.5        # used by the what-if simulator
TARGET_WATER_RECYCLING = 95.0


# ------------------------------------------------------------ factor points
def food_coverage_ratio(food_days_stock, mission_days):
    """Days of food stocked divided by planned mission length."""
    if mission_days <= 0:
        raise ValueError("mission_days must be positive")
    if food_days_stock < 0:
        raise ValueError("food_days_stock cannot be negative")
    return round(food_days_stock / mission_days, 2)


def food_risk_points(ratio):
    """Illustrative risk points from food coverage ratio."""
    if ratio >= 1.5:
        return 0
    elif ratio >= 1.0:
        return 3
    elif ratio >= 0.75:
        return 10
    else:
        return 20


def water_risk_points(recycling_percent):
    """Illustrative risk points from the water-recycling efficiency (0-100 %)."""
    if recycling_percent < 0 or recycling_percent > 100:
        raise ValueError("water_recycling_percent must be between 0 and 100")
    if recycling_percent >= 90:
        return 0
    elif recycling_percent >= 70:
        return 4
    elif recycling_percent >= 50:
        return 10
    else:
        return 18


def systems_risk_points(oxygen_system, radiation_shielding, power_source):
    """Points from the three categorical life-support systems."""
    if oxygen_system not in OXYGEN_SYSTEMS:
        raise ValueError(f"oxygen_system must be one of {OXYGEN_SYSTEMS}")
    if radiation_shielding not in SHIELDING_TYPES:
        raise ValueError(f"radiation_shielding must be one of {SHIELDING_TYPES}")
    if power_source not in POWER_SOURCES:
        raise ValueError(f"power_source must be one of {POWER_SOURCES}")
    return (OXYGEN_POINTS[oxygen_system] + SHIELDING_POINTS[radiation_shielding]
            + POWER_POINTS[power_source])


def crew_risk_points(crew_size, medical_officer, backup_habitat):
    """Points from crew/organisation factors."""
    points = 0
    if crew_size < SMALL_CREW_LIMIT:
        points += 5            # isolation / no skill redundancy
    if not medical_officer:
        points += 6
    if not backup_habitat:
        points += 8
    return points


def calculate_risk_score(crew_size, mission_days, food_days_stock, water_recycling_percent,
                         oxygen_system, radiation_shielding, power_source,
                         medical_officer, backup_habitat):
    """Combines all factors into one risk score, clamped to [0, 100]."""
    ratio = food_coverage_ratio(food_days_stock, mission_days)
    score = (
        food_risk_points(ratio)
        + water_risk_points(water_recycling_percent)
        + systems_risk_points(oxygen_system, radiation_shielding, power_source)
        + crew_risk_points(crew_size, medical_officer, backup_habitat)
    )
    return max(0, min(100, score))


def categorize_risk(risk_score):
    if risk_score < 0 or risk_score > 100:
        raise ValueError("risk_score must be between 0 and 100")
    if risk_score <= RISK_LOW_MAX:
        return "Low Risk"
    elif risk_score <= RISK_MODERATE_MAX:
        return "Moderate Risk"
    return "High Risk"


def survival_probability(risk_score):
    """Illustrative mission survival probability (%), floored at 0."""
    if risk_score < 0 or risk_score > 100:
        raise ValueError("risk_score must be between 0 and 100")
    return round(max(MIN_SURVIVAL_PERCENT, 100 - risk_score * SURVIVAL_PENALTY_RATE), 1)


def predicted_survival_days(mission_days, risk_score):
    """Expected survivable days = planned mission days x survival probability."""
    if mission_days < MIN_MISSION_DAYS or mission_days > MAX_MISSION_DAYS:
        raise ValueError(f"mission_days must be between {MIN_MISSION_DAYS} and {MAX_MISSION_DAYS}")
    return round(mission_days * survival_probability(risk_score) / 100.0, 1)


def validate_inputs(crew_size, mission_days, food_days_stock, water_recycling_percent):
    if crew_size < MIN_CREW or crew_size > MAX_CREW:
        raise ValueError(f"crew_size must be between {MIN_CREW} and {MAX_CREW}")
    if mission_days < MIN_MISSION_DAYS or mission_days > MAX_MISSION_DAYS:
        raise ValueError(f"mission_days must be between {MIN_MISSION_DAYS} and {MAX_MISSION_DAYS}")
    if food_days_stock < 0 or food_days_stock > MAX_FOOD_DAYS:
        raise ValueError(f"food_days_stock must be between 0 and {MAX_FOOD_DAYS}")
    if water_recycling_percent < 0 or water_recycling_percent > 100:
        raise ValueError("water_recycling_percent must be between 0 and 100")


def compute_assessment(crew_size, mission_days, food_days_stock, water_recycling_percent,
                       oxygen_system, radiation_shielding, power_source,
                       medical_officer, backup_habitat):
    """Top-level orchestration used by the Flask route."""
    validate_inputs(crew_size, mission_days, food_days_stock, water_recycling_percent)
    score = calculate_risk_score(crew_size, mission_days, food_days_stock, water_recycling_percent,
                                 oxygen_system, radiation_shielding, power_source,
                                 medical_officer, backup_habitat)
    return {
        "food_ratio": food_coverage_ratio(food_days_stock, mission_days),
        "risk_score": score,
        "risk_category": categorize_risk(score),
        "survival_probability": survival_probability(score),
        "predicted_survival_days": predicted_survival_days(mission_days, score),
    }


# ======================================================================
# Breakdown, advice, what-if, feedback validation
# ======================================================================
HELPFUL_CHOICES = ('yes', 'somewhat', 'no')
MAX_COMMENT_LENGTH = 500


def risk_breakdown(crew_size, mission_days, food_days_stock, water_recycling_percent,
                   oxygen_system, radiation_shielding, power_source,
                   medical_officer, backup_habitat):
    """Per-factor contribution (sums to the unclamped score). Used by the factor chart."""
    systems_risk_points(oxygen_system, radiation_shielding, power_source)  # validates
    ratio = food_coverage_ratio(food_days_stock, mission_days)
    return [
        {"key": "food", "label": "Food supply", "points": food_risk_points(ratio), "modifiable": True},
        {"key": "water", "label": "Water recycling", "points": water_risk_points(water_recycling_percent), "modifiable": True},
        {"key": "oxygen", "label": "Oxygen system", "points": OXYGEN_POINTS[oxygen_system], "modifiable": True},
        {"key": "shielding", "label": "Radiation shield", "points": SHIELDING_POINTS[radiation_shielding], "modifiable": True},
        {"key": "power", "label": "Power source", "points": POWER_POINTS[power_source], "modifiable": True},
        {"key": "medical", "label": "Medical officer", "points": 0 if medical_officer else 6, "modifiable": True},
        {"key": "backup", "label": "Backup habitat", "points": 0 if backup_habitat else 8, "modifiable": True},
        {"key": "crew", "label": "Crew size", "points": 5 if crew_size < SMALL_CREW_LIMIT else 0, "modifiable": False},
    ]


_CATEGORY_HEADLINES = {
    "Low Risk": "Your habitat plan is in the low-risk band. Keep your redundancy and monitoring in place.",
    "Moderate Risk": "Your habitat plan is in the moderate-risk band. A few targeted upgrades can move it down a band.",
    "High Risk": "Your habitat plan is in the high-risk band. Fix the high-priority gaps before committing to the mission.",
}


def get_recommendations(risk_category, crew_size, mission_days, food_days_stock,
                        water_recycling_percent, oxygen_system, radiation_shielding,
                        power_source, medical_officer, backup_habitat):
    """Returns {"headline": str, "items": [{priority, title, text}]} sorted high -> low."""
    if risk_category not in _CATEGORY_HEADLINES:
        raise ValueError("Unknown risk category")
    ratio = food_coverage_ratio(food_days_stock, mission_days)
    items = []

    if ratio < 0.75:
        items.append({"priority": "high", "title": "Stock far more food",
                      "text": f"Your food covers only {ratio:.2f}x the mission length (+20 points). "
                              "Aim for at least 1.5x to leave a safety margin for delays."})
    elif ratio < 1.0:
        items.append({"priority": "high", "title": "Increase food reserves",
                      "text": f"Food coverage is {ratio:.2f}x the mission (+10 points). Reach at least 1.0x, ideally 1.5x."})
    elif ratio < 1.5:
        items.append({"priority": "low", "title": "Add a food safety margin",
                      "text": f"Food coverage is {ratio:.2f}x (+3 points). A 1.5x reserve removes this factor."})

    if water_recycling_percent < 50:
        items.append({"priority": "high", "title": "Upgrade water recycling",
                      "text": f"Recycling at {water_recycling_percent:g}% adds +18 points. Target 90% or more."})
    elif water_recycling_percent < 70:
        items.append({"priority": "medium", "title": "Improve water recycling",
                      "text": f"Recycling at {water_recycling_percent:g}% adds +10 points. Target 90% or more."})
    elif water_recycling_percent < 90:
        items.append({"priority": "low", "title": "Push water recycling to 90%+",
                      "text": f"Recycling at {water_recycling_percent:g}% adds +4 points."})

    if oxygen_system == 'limited':
        items.append({"priority": "high", "title": "Add in-situ oxygen production",
                      "text": "Limited backup oxygen is the largest systems risk (+20 points). "
                              "Oxygen production from Martian CO2 (ISRU) removes it."})
    elif oxygen_system == 'stored':
        items.append({"priority": "medium", "title": "Move from stored to produced oxygen",
                      "text": "Stored tanks add +8 points. In-situ production removes the resupply dependency."})

    if radiation_shielding == 'minimal':
        items.append({"priority": "high", "title": "Improve radiation shielding",
                      "text": "Minimal shielding adds +18 points. Cover the habitat with regolith or move it underground."})
    elif radiation_shielding == 'partial':
        items.append({"priority": "medium", "title": "Complete the radiation shielding",
                      "text": "Partial shielding adds +8 points. Full regolith cover removes it."})

    if power_source == 'solar_only':
        items.append({"priority": "high", "title": "Add a dust-storm-proof power source",
                      "text": "Solar-only power (+12 points) fails during global dust storms. Add a nuclear source."})
    elif power_source == 'solar_battery':
        items.append({"priority": "low", "title": "Consider nuclear backup power",
                      "text": "Solar plus batteries adds +5 points. A small reactor removes it."})

    if not medical_officer:
        items.append({"priority": "medium", "title": "Include a trained medical officer",
                      "text": "No medical officer adds +6 points. Cross-train at least one crew member."})
    if not backup_habitat:
        items.append({"priority": "medium", "title": "Build a backup habitat module",
                      "text": "No backup habitat adds +8 points. A second sealed module protects against a single breach."})
    if crew_size < SMALL_CREW_LIMIT:
        items.append({"priority": "low", "title": "Consider a larger crew",
                      "text": f"A crew of {crew_size} adds +5 points for isolation and low skill redundancy."})

    if not items:
        items.append({"priority": "low", "title": "Maintain your redundancy",
                      "text": "No risk-raising factors were found. Keep testing every life-support system regularly."})

    order = {"high": 0, "medium": 1, "low": 2}
    items.sort(key=lambda i: order[i["priority"]])
    return {"headline": _CATEGORY_HEADLINES[risk_category], "items": items}


def what_if_scenarios(crew_size, mission_days, food_days_stock, water_recycling_percent,
                      oxygen_system, radiation_shielding, power_source,
                      medical_officer, backup_habitat):
    """
    Simulates upgrading ONE factor at a time (plus all together). Only scenarios
    that change something are returned.
    Each: {label, new_score, new_category, new_probability, new_days, days_gained, score_change}
    """
    base = dict(crew_size=crew_size, mission_days=mission_days, food_days_stock=food_days_stock,
                water_recycling_percent=water_recycling_percent, oxygen_system=oxygen_system,
                radiation_shielding=radiation_shielding, power_source=power_source,
                medical_officer=medical_officer, backup_habitat=backup_habitat)
    base_score = calculate_risk_score(**base)
    base_days = predicted_survival_days(mission_days, base_score)

    changes = []
    if food_coverage_ratio(food_days_stock, mission_days) < NEUTRAL_FOOD_RATIO:
        changes.append(("Stock 1.5x food", {"food_days_stock": int(-(-mission_days * NEUTRAL_FOOD_RATIO // 1))}))
    if water_recycling_percent < 90:
        changes.append(("Recycle 95% of water", {"water_recycling_percent": TARGET_WATER_RECYCLING}))
    if oxygen_system != 'isru':
        changes.append(("Produce oxygen on-site", {"oxygen_system": 'isru'}))
    if radiation_shielding != 'regolith':
        changes.append(("Bury habitat in regolith", {"radiation_shielding": 'regolith'}))
    if power_source != 'nuclear':
        changes.append(("Add nuclear power", {"power_source": 'nuclear'}))
    if not medical_officer:
        changes.append(("Add medical officer", {"medical_officer": True}))
    if not backup_habitat:
        changes.append(("Add backup habitat", {"backup_habitat": True}))

    def run(label, overrides):
        params = dict(base)
        params.update(overrides)
        score = calculate_risk_score(**params)
        days = predicted_survival_days(mission_days, score)
        return {"label": label, "new_score": score, "new_category": categorize_risk(score),
                "new_probability": survival_probability(score), "new_days": days,
                "days_gained": round(days - base_days, 1), "score_change": score - base_score}

    scenarios = [run(label, ov) for label, ov in changes]
    if len(changes) > 1:
        combined = {}
        for _, ov in changes:
            combined.update(ov)
        scenarios.append(run("All upgrades together", combined))
    return scenarios


def validate_feedback(rating, helpful, comment):
    """Returns (rating:int, helpful:str, comment:str) or raises ValueError (user-facing message)."""
    try:
        rating = int(rating)
    except (TypeError, ValueError):
        raise ValueError("Please select a star rating from 1 to 5.")
    if rating < 1 or rating > 5:
        raise ValueError("Rating must be between 1 and 5.")
    if helpful not in HELPFUL_CHOICES:
        raise ValueError("Please tell us whether the advice was helpful.")
    comment = (comment or "").strip()
    if len(comment) > MAX_COMMENT_LENGTH:
        raise ValueError(f"Comment must be at most {MAX_COMMENT_LENGTH} characters.")
    return rating, helpful, comment

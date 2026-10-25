# STQA Mini Project — Mars Colony Survival & Habitability Estimator
*(OOMD case study: Mars Life Prediction / Habitat Survival System)*

> Copy each section into your college template (Abstract, Introduction, System Requirements, Methodology, Implementation, Test Cases & Bug Taxonomy, Test Execution Report, Test Result Report, Conclusion, References). All numbers in sections 7–8 come from the actual test run.

## One-line title
**Design, Implementation and Black-Box/White-Box Testing of a Web-Based Mars Colony Survival & Habitability Estimator using Python, Flask and pytest**

## 1. Abstract
This project implements a web application that estimates the survival prospects of a Mars habitat mission. A mission planner registers, logs in and enters mission and habitat details (crew size, mission length, food stock, water recycling efficiency, oxygen system, radiation shielding, power source, medical officer, backup habitat). A rule-based model computes a risk score (0–100), a risk category (Low / Moderate / High), a survival probability and the expected number of survivable days. The results are shown on a dashboard with charts, tailored advice and a what-if simulator, and users can submit quick feedback. The system is tested at unit and integration level using white-box and black-box techniques (statement/branch coverage, equivalence partitioning, boundary value analysis) with pytest. **205 automated tests passed with 99 % statement coverage.** The prediction model is illustrative and academic only.

## 2. Introduction
- **Problem:** Early evaluation of whether a planned Mars habitat is safe is complex; planners need a quick, explainable estimate.
- **Objective:** Build a real web application with a database and test it systematically.
- **Scope:** Rule-based educational model; not real mission-planning software.
- **Testing objective:** Verify correctness of the risk calculation at every threshold, input validation, authentication, data isolation between users, charts, advice, and feedback.

## 3. System Requirements
| Item | Detail |
|---|---|
| Language | Python 3.13 |
| Framework | Flask 3.1.3, Flask-SQLAlchemy 3.1.1 |
| Database | SQLite (file `instance/mars_prediction.db`) |
| Frontend | Jinja2 templates, CSS, inline SVG charts (no internet needed) |
| Testing tools | pytest 9.1.1, pytest-cov 7.1.0, Flask test client |
| Hardware | Any PC, 4 GB RAM |

**Functional requirements:** FR1 register/login/logout · FR2 enter mission data with validation · FR3 compute risk score, category, survival % and days · FR4 store and list assessments per user · FR5 dashboard with charts · FR6 tailored advice · FR7 what-if simulator · FR8 feedback with rating, helpfulness and comment · FR9 users cannot see other users' data.

## 4. Methodology / Design
Layered architecture (see `design_diagrams/01_architecture.png`): templates → Flask routes → framework-free business logic → SQLAlchemy models → SQLite. The business logic is kept independent of Flask so it can be unit tested in isolation. Diagrams: ER (02), use case (03), activity (04).

**Risk model (illustrative):**
| Factor | Points |
|---|---|
| Food coverage (stock ÷ mission days) | ≥1.5: 0 · ≥1.0: 3 · ≥0.75: 10 · else 20 |
| Water recycling % | ≥90: 0 · ≥70: 4 · ≥50: 10 · else 18 |
| Oxygen system | in-situ 0 · stored 8 · limited 20 |
| Radiation shielding | regolith 0 · partial 8 · minimal 18 |
| Power source | nuclear 0 · solar+battery 5 · solar only 12 |
| Crew size < 4 | +5 |
| No medical officer | +6 |
| No backup habitat | +8 |

Score = sum, clamped to 0–100 (the raw worst case is 107, so clamping is reachable). Categories: Low ≤ 25, Moderate ≤ 55, High > 55. Survival probability = 100 − 0.9 × score (%). Predicted survivable days = mission days × probability.

## 5. Implementation (modules)
| File | Purpose |
|---|---|
| `business_logic.py` | scoring, categories, survival, breakdown, advice, what-if, feedback validation |
| `charts.py` | inline SVG: risk gauge, probability meter, factor bars, mission-vs-survival bars, what-if bars, trend line |
| `models.py` | User, Assessment, Feedback tables |
| `app.py` | routes, session authentication, input validation |
| `templates/`, `static/` | pages and styling |

## 6. Test Plan
**Features to be tested:** authentication; mission input validation; risk calculation; categorisation; survival calculation; assessment persistence; access control; dashboard charts; advice; what-if; feedback; history and trend.
**Features not tested:** real-world accuracy of the model, performance/load, browser compatibility.
**Approach:** white-box unit tests (branch/statement coverage), black-box tests via HTTP (ECP, BVA), integration tests (auth + logic + DB).
**Entry criteria:** code complete, environment ready. **Exit criteria:** all tests pass, ≥ 90 % statement coverage, no open critical/major defect.
**Pass/fail criterion per test:** actual result equals expected result.

### Bug taxonomy used
| Category | Example for this project |
|---|---|
| Calculation / logic | wrong threshold, off-by-one at boundary |
| Input validation | accepts crew size 0, negative food stock |
| Boundary | 1.5 food ratio classified as 3 points instead of 0 |
| Security / access control | one user views another user's mission |
| Data integrity | invalid assessment saved to DB |
| Exception handling | ZeroDivisionError instead of a user message |
| UI / presentation | chart label clipped, wrong category colour |

## 7. Test Cases (selected; 205 automated in total)
| ID | Technique | Scenario | Input | Expected | Test function |
|---|---|---|---|---|---|
| TC01 | Unit / BVA | food ratio at 1.5 | ratio 1.5 | 0 points | `test_food_points_boundaries[1.5-0]` |
| TC02 | Unit / BVA | food ratio just below 1.0 | 0.99 | 10 points | `test_food_points_boundaries[0.99-10]` |
| TC03 | Unit / BVA | water 90 % vs 89.9 % | 90 / 89.9 | 0 / 4 points | `test_water_points_boundaries` |
| TC04 | Unit | water outside range | −0.1, 100.1 | ValueError | `test_water_rejects_out_of_range` |
| TC05 | Unit | invalid system choice | "coal" | ValueError | `test_systems_rejects_invalid_choice` |
| TC06 | Unit | zero mission days | 0 | ValueError (no ZeroDivisionError) | `test_food_ratio_rejects_non_positive_mission` |
| TC07 | Unit | score clamp | worst case (raw 107) | 100 | `test_score_clamped_at_100` |
| TC08 | Unit / BVA | category boundaries | 25 / 26 / 55 / 56 | Low / Moderate / Moderate / High | `test_category_boundaries` |
| TC09 | Unit | survival probability | score 62 | 44.2 % | `test_survival_probability_values` |
| TC10 | Unit | known profile | crew 6, 500 d, 600 food, 80 % … | 28, Moderate, 74.8 %, 374 d | `test_compute_assessment_keys_and_values` |
| TC11 | Black-box / ECP | non-numeric crew size | "abc" | "valid numeric values" message | `test_non_numeric_input_rejected` |
| TC12 | Black-box / BVA | crew size 0 / 101 | 0, 101 | rejected | `test_boundary_just_outside_rejected` |
| TC13 | Black-box / BVA | crew size 1 / 100 | 1, 100 | accepted | `test_boundary_at_limit_accepted` |
| TC14 | Black-box | password 5 vs 6 chars | 5 / 6 | reject / accept | `test_register_validation`, `test_register_password_boundary_6_accepted` |
| TC15 | Black-box | protected pages while logged out | GET /history etc. | redirect to login | `test_protected_pages_require_login` |
| TC16 | Black-box (security) | cross-user access | user B opens user A's assessment | access denied | `test_cross_user_access_denied` |
| TC17 | Black-box (security) | XSS in mission name | `<script>` | escaped | `test_xss_in_mission_name_is_escaped` |
| TC18 | Integration | persistence | valid form | DB row equals computed result | `test_assessment_persisted_with_computed_values` |
| TC19 | Integration | invalid input | crew 0 | nothing saved | `test_invalid_assessment_not_persisted` |
| TC20 | Integration | history isolation | two users | each sees only own rows | `test_history_lists_only_own_assessments` |
| TC21 | White-box | advice tiers | food 100/400/600 | three different advice items | `test_food_advice_tiers` |
| TC22 | White-box | what-if combined | worst-to-best | best scenario is Low Risk | `test_all_changes_scenario_is_best_and_low` |
| TC23 | Black-box | feedback validation | rating 0/6/abc | rejected with message | `test_invalid_feedback_rejected` |
| TC24 | Integration | feedback ownership | other user's assessment id | rejected, nothing stored | `test_cannot_attach_to_other_users_assessment` |

## 8. Test Execution & Result Report (real run)
**Environment:** Python 3.13.16, Flask 3.1.3, pytest 9.1.1, pytest-cov 7.1.0.
Command: `python -m pytest -v` (coverage: `python -m pytest --cov=app --cov=models --cov=business_logic --cov=charts`)

| Test module | Level / technique | Tests | Passed | Failed |
|---|---|---|---|---|
| `test_unit_whitebox.py` | Unit, white-box | 74 | 74 | 0 |
| `test_blackbox_api.py` | Black-box (ECP/BVA, security) | 51 | 51 | 0 |
| `test_integration.py` | Integration | 4 | 4 | 0 |
| `test_enhanced_features.py` | Mixed (breakdown, advice, what-if, charts, feedback) | 76 | 76 | 0 |
| **Total** | | **205** | **205** | **0** |

**Coverage:**
| File | Statements | Missed | Coverage |
|---|---|---|---|
| business_logic.py | 183 | 0 | 100 % |
| charts.py | 98 | 0 | 100 % |
| models.py | 47 | 0 | 100 % |
| app.py | 155 | 2 | 99 % (the two lines under `if __name__ == "__main__"`) |
| **Total** | **483** | **2** | **99 %** |

Run time ≈ 16 seconds.

### Defect demonstration (mutation check)
To show the tests detect faults, three defects were injected into a scratch copy of the code. Each was caught:
| ID | Injected defect | Taxonomy | Caught by | Observed result |
|---|---|---|---|---|
| DEF-01 | removed zero-mission-days guard | Exception handling | `test_food_ratio_rejects_non_positive_mission[10-0]` | `ZeroDivisionError: division by zero` |
| DEF-02 | `ratio >= 1.5` changed to `ratio > 1.5` | Boundary | `test_food_points_boundaries[1.5-0]`, `test_food_scenario_targets_1_5x` | 2 failed, 203 passed |
| DEF-03 | owner check removed in `/assessment/<id>` | Security | `test_cross_user_access_denied` | 1 failed, 204 passed |

The original code was restored and all 205 tests pass again. (Say in the viva that these were injected deliberately to demonstrate fault detection.)

### Acceptance judgement
| Criterion | Target | Result | Met |
|---|---|---|---|
| All test cases pass | 100 % | 205 / 205 | Yes |
| Statement coverage | ≥ 90 % | 99 % | Yes |
| Open critical/major defects | 0 | 0 | Yes |
| Cross-user data isolation | verified | verified (TC16, TC20, TC24) | Yes |
**Verdict: ACCEPTED** for its academic purpose.

## 9. Conclusion
The estimator works end-to-end as a real web application, and systematic white-box and black-box testing found the code behaves as specified at every boundary of the model. Limitations: the model is illustrative, uses a development server, and has no performance or browser-compatibility testing. Future work: real mission data, role-based admin, load testing with JMeter or Locust, Selenium UI tests, CI pipeline.

## 10. References
1. Flask documentation — https://flask.palletsprojects.com
2. Flask-SQLAlchemy documentation — https://flask-sqlalchemy.palletsprojects.com
3. pytest documentation — https://docs.pytest.org
4. pytest-cov documentation — https://pytest-cov.readthedocs.io
5. Myers, G. J., *The Art of Software Testing*, Wiley.
6. Pressman, R. S., *Software Engineering: A Practitioner's Approach*, McGraw-Hill.

## Viva cheat-sheet
- **Why a framework-free `business_logic.py`?** So it can be unit tested without a server or database.
- **Why an in-memory DB for tests?** Isolation, speed, the real DB is never touched.
- **White-box vs black-box here?** White-box: `test_unit_whitebox.py` targets branches. Black-box: `test_blackbox_api.py` only uses HTTP inputs/outputs.
- **Where is BVA?** Crew 0/1/100/101, mission days 0/1/1825/1826, water −0.1/0/100/100.1, ratio 0.74/0.75/1.49/1.5, score 25/26/55/56.
- **Is the model accurate?** No, it is illustrative; the project is about testing, not prediction accuracy.
- **Why is 99 % not 100 %?** The two missed lines start the dev server and are not run under tests.

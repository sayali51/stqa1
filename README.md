# Mars Colony Survival & Habitability Estimator

Educational Flask app (STQA mini project, OOMD "Mars Life Prediction System") with charts, tailored advice,
a what-if simulator, feedback and a pytest suite. **Not real mission-planning software.**

## Run
```
pip install -r requirements.txt
python app.py
```
Open http://localhost:5000, register, log in and create an assessment.

## Test
```
python -m pytest -v
python -m pytest --cov=app --cov=models --cov=business_logic --cov=charts --cov-report=term-missing
```
Result: 205 passed, 99% coverage.

## Structure
```
app.py  models.py  business_logic.py  charts.py  requirements.txt
templates/  static/  tests/  design_diagrams/
```

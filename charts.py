"""
Pure inline-SVG chart generators (no JavaScript, no CDN, works offline).
Every function returns a markupsafe.Markup string so Jinja2 will not
escape it. User-supplied text is HTML-escaped before embedding.
Meaning is never carried by colour alone: values are also printed as text.
"""
import math
from html import escape
from markupsafe import Markup

RISK_COLORS = {"Low Risk": "#2e8b57", "Moderate Risk": "#d98e04", "High Risk": "#c0392b"}


def _arc(cx, cy, r, a1, a2):
    """SVG arc on a semicircle gauge. Angles in degrees, 0=left, 180=right."""
    x1, y1 = cx - r * math.cos(math.radians(a1)), cy - r * math.sin(math.radians(a1))
    x2, y2 = cx - r * math.cos(math.radians(a2)), cy - r * math.sin(math.radians(a2))
    return f"M {x1:.1f} {y1:.1f} A {r} {r} 0 0 1 {x2:.1f} {y2:.1f}"


def risk_gauge(score, category):
    """Semicircular gauge, 0-100, bands: Low 0-20, Moderate 20-50, High 50-100."""
    score = max(0, min(100, float(score)))
    cx, cy, r = 150, 150, 110
    bands = [(0, 20, RISK_COLORS["Low Risk"]), (20, 50, RISK_COLORS["Moderate Risk"]),
             (50, 100, RISK_COLORS["High Risk"])]
    parts = [f'<svg class="chart" viewBox="0 0 300 210" role="img" '
             f'aria-label="Risk gauge: score {score:.0f} out of 100, {escape(category)}">']
    for lo, hi, color in bands:
        parts.append(f'<path d="{_arc(cx, cy, r, lo * 1.8, hi * 1.8)}" fill="none" '
                     f'stroke="{color}" stroke-width="22"/>')
    ang = score * 1.8
    nx, ny = cx - (r - 18) * math.cos(math.radians(ang)), cy - (r - 18) * math.sin(math.radians(ang))
    parts.append(f'<line x1="{cx}" y1="{cy}" x2="{nx:.1f}" y2="{ny:.1f}" stroke="currentColor" '
                 f'stroke-width="4" stroke-linecap="round"/>')
    parts.append(f'<circle cx="{cx}" cy="{cy}" r="7" fill="currentColor"/>')
    parts.append(f'<text x="{cx}" y="{cy + 30}" text-anchor="middle" font-size="22" '
                 f'font-weight="700" fill="currentColor">{score:.0f} / 100</text>')
    parts.append(f'<text x="{cx}" y="{cy + 48}" text-anchor="middle" font-size="13" '
                 f'fill="currentColor">{escape(category)}</text>')
    parts.append(f'<text x="{cx - r}" y="{cy + 16}" text-anchor="middle" font-size="10" fill="currentColor">0</text>')
    parts.append(f'<text x="{cx + r}" y="{cy + 16}" text-anchor="middle" font-size="10" fill="currentColor">100</text>')
    parts.append('</svg>')
    return Markup("".join(parts))


def factor_bar_chart(breakdown):
    """Horizontal bars, one per factor. Negative points extend left (protective)."""
    row_h, left, width, zero_x, scale = 34, 130, 520, 330, 10  # px per point
    height = row_h * len(breakdown) + 20
    parts = [f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" '
             f'aria-label="Risk points contributed by each factor">']
    parts.append(f'<line x1="{zero_x}" y1="5" x2="{zero_x}" y2="{height - 10}" stroke="currentColor" opacity="0.4"/>')
    for i, f in enumerate(breakdown):
        y = 10 + i * row_h
        pts = f["points"]
        w = abs(pts) * scale
        x = zero_x if pts >= 0 else zero_x - w
        color = "#c0392b" if pts > 0 else ("#2e8b57" if pts < 0 else "#8a94a6")
        parts.append(f'<text x="{left - 8}" y="{y + 16}" text-anchor="end" font-size="13" '
                     f'fill="currentColor">{escape(f["label"])}</text>')
        if w > 0:
            parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="22" rx="3" fill="{color}"/>')
        label_x = zero_x + w + 6 if pts >= 0 else zero_x - w - 6
        anchor = "start" if pts >= 0 else "end"
        sign = f"+{pts}" if pts > 0 else str(pts)
        parts.append(f'<text x="{label_x}" y="{y + 16}" text-anchor="{anchor}" font-size="13" '
                     f'font-weight="600" fill="currentColor">{sign}</text>')
    parts.append('</svg>')
    return Markup("".join(parts))


def survival_comparison_chart(mission_days, predicted_days):
    """Compares the planned mission length with the predicted survivable days."""
    top = max(float(mission_days), float(predicted_days), 1.0)
    rows = [("Planned mission", float(mission_days), "#8a94a6"),
            ("Predicted survivable", float(predicted_days), "#b5482a")]
    parts = ['<svg class="chart" viewBox="0 0 560 120" role="img" '
             f'aria-label="Planned mission {mission_days:g} days, predicted survivable {predicted_days:g} days">']
    for i, (label, val, color) in enumerate(rows):
        y = 12 + i * 50
        w = 280 * val / top
        parts.append(f'<text x="150" y="{y + 20}" text-anchor="end" font-size="13" fill="currentColor">{label}</text>')
        parts.append(f'<rect x="160" y="{y}" width="{max(w, 2):.1f}" height="28" rx="3" fill="{color}"/>')
        parts.append(f'<text x="{168 + w:.1f}" y="{y + 20}" font-size="13" font-weight="600" '
                     f'fill="currentColor">{val:g} days</text>')
    parts.append('</svg>')
    return Markup("".join(parts))


def probability_meter(probability):
    """Single horizontal bar showing survival probability (0-100 %), label above the bar."""
    p = max(0.0, min(100.0, float(probability)))
    color = "#2e8b57" if p >= 75 else ("#d98e04" if p >= 45 else "#c0392b")
    return Markup(
        '<svg class="chart" viewBox="0 0 560 80" role="img" '
        f'aria-label="Survival probability {p:.1f} percent">'
        f'<text x="10" y="20" font-size="14" font-weight="700" fill="currentColor">{p:.1f}% survival probability</text>'
        '<rect x="10" y="32" width="540" height="24" rx="12" fill="currentColor" opacity="0.12"/>'
        f'<rect x="10" y="32" width="{max(5.4 * p, 0):.1f}" height="24" rx="12" fill="{color}"/>'
        '</svg>')


def what_if_chart(current_score, scenarios):
    """Bars of resulting risk score per scenario, with the current score as first bar."""
    rows = [("Current", current_score)] + [(s["label"], s["new_score"]) for s in scenarios]
    row_h = 34
    height = row_h * len(rows) + 10
    parts = [f'<svg class="chart" viewBox="0 0 560 {height}" role="img" '
             f'aria-label="Risk score under each what-if scenario">']
    for i, (label, val) in enumerate(rows):
        y = 6 + i * row_h
        w = max(0, min(100, val)) * 3.0
        color = "#7a2e1d" if i == 0 else "#2e8b57"
        parts.append(f'<text x="190" y="{y + 16}" text-anchor="end" font-size="13" fill="currentColor">{escape(label)}</text>')
        parts.append(f'<rect x="200" y="{y}" width="{max(w, 2):.1f}" height="22" rx="3" fill="{color}"/>')
        parts.append(f'<text x="{208 + w:.1f}" y="{y + 16}" font-size="13" font-weight="600" '
                     f'fill="currentColor">{val:g}</text>')
    parts.append('</svg>')
    return Markup("".join(parts))


def trend_chart(scores):
    """Line chart of risk scores over a user's assessments (oldest -> newest)."""
    if not scores:
        return Markup('<p class="muted">No assessments yet.</p>')
    w, h, left, right, top, bottom = 560, 240, 40, 20, 15, 30
    pw, ph = w - left - right, h - top - bottom

    def y_of(v):
        return top + ph * (1 - max(0, min(100, v)) / 100.0)

    def x_of(i):
        return left + (pw / 2 if len(scores) == 1 else pw * i / (len(scores) - 1))

    parts = [f'<svg class="chart" viewBox="0 0 {w} {h}" role="img" '
             f'aria-label="Risk score trend across {len(scores)} assessments">']
    for t, name in ((20, "Low/Moderate"), (50, "Moderate/High")):
        parts.append(f'<line x1="{left}" y1="{y_of(t):.1f}" x2="{w - right}" y2="{y_of(t):.1f}" '
                     f'stroke="currentColor" opacity="0.3" stroke-dasharray="4 4"/>')
        parts.append(f'<text x="{left - 5}" y="{y_of(t) + 4:.1f}" text-anchor="end" font-size="10" fill="currentColor">{t}</text>')
    parts.append(f'<text x="{left - 5}" y="{y_of(0) + 4:.1f}" text-anchor="end" font-size="10" fill="currentColor">0</text>')
    pts = " ".join(f"{x_of(i):.1f},{y_of(v):.1f}" for i, v in enumerate(scores))
    if len(scores) > 1:
        parts.append(f'<polyline points="{pts}" fill="none" stroke="#7a2e1d" stroke-width="2.5"/>')
    for i, v in enumerate(scores):
        parts.append(f'<circle cx="{x_of(i):.1f}" cy="{y_of(v):.1f}" r="5" fill="#7a2e1d"/>')
        parts.append(f'<text x="{x_of(i):.1f}" y="{y_of(v) - 10:.1f}" text-anchor="middle" font-size="11" '
                     f'font-weight="600" fill="currentColor">{v:g}</text>')
        parts.append(f'<text x="{x_of(i):.1f}" y="{h - 10}" text-anchor="middle" font-size="10" '
                     f'fill="currentColor">#{i + 1}</text>')
    parts.append('</svg>')
    return Markup("".join(parts))

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models_db import Visit

CLASS_RANK = {"Normal": 0, "Suspect": 1, "Pathological": 2}
RANK_CLASS = {v: k for k, v in CLASS_RANK.items()}


def _linear_trend(values: list[float]) -> float:
    """Returns slope of a simple linear fit; positive = worsening."""
    n = len(values)
    if n < 2:
        return 0.0
    xs = list(range(n))
    x_mean = sum(xs) / n
    y_mean = sum(values) / n
    num = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, values))
    den = sum((x - x_mean) ** 2 for x in xs)
    return num / den if den else 0.0


def aggregate_risk(visits: list[Visit]) -> dict:
    """
    Heuristic aggregate risk across all visits for one patient.

    Logic:
      - worst_rank = max predicted class rank across visits
      - ASTV trend: negative slope (decreasing variability) → raises risk
      - DL trend:   positive slope (more decelerations) → raises risk
      - Final class = worst_rank + 1 if trends are worsening, else worst_rank
    """
    if not visits:
        return {
            "aggregate_class": "Normal",
            "trend": "insufficient_data",
            "explanation": ["Нет приёмов для анализа"],
            "visits": [],
        }

    sorted_visits = sorted(visits, key=lambda v: v.visit_date or v.created_at)

    worst_rank = 0
    astv_vals: list[float] = []
    lb_vals:   list[float] = []
    dl_vals:   list[float] = []

    rows = []
    for v in sorted_visits:
        rank = CLASS_RANK.get(v.predicted_class, 0)
        worst_rank = max(worst_rank, rank)

        feats = v.features or {}
        astv = feats.get("ASTV")
        lb   = feats.get("LB")
        dl   = feats.get("DL")

        if astv is not None:
            astv_vals.append(float(astv))
        if lb is not None:
            lb_vals.append(float(lb))
        if dl is not None:
            dl_vals.append(float(dl))

        rows.append({
            "visit_id":         v.id,
            "visit_date":       (v.visit_date or v.created_at).isoformat()
                                if (v.visit_date or v.created_at) else None,
            "gestational_week": v.gestational_week,
            "predicted_class":  v.predicted_class,
            "doctor_label":     v.doctor_label,
            "astv":             astv,
            "lb":               lb,
            "dl":               dl,
        })

    explanations: list[str] = []
    trend_score = 0

    astv_slope = _linear_trend(astv_vals)
    dl_slope   = _linear_trend(dl_vals)
    lb_slope   = _linear_trend(lb_vals)

    if len(astv_vals) >= 2:
        if astv_slope < -0.5:
            explanations.append("Вариабельность ЧСС (ASTV) снижается — негативный тренд")
            trend_score += 1
        elif astv_slope > 0.5:
            explanations.append("Вариабельность ЧСС (ASTV) растёт — позитивный тренд")
            trend_score -= 1

    if len(dl_vals) >= 2:
        if dl_slope > 0.1:
            explanations.append("Число децелераций (DL) нарастает — признак дистресса")
            trend_score += 1
        elif dl_slope < -0.1:
            explanations.append("Число децелераций (DL) снижается — состояние улучшается")
            trend_score -= 1

    if len(lb_vals) >= 2:
        if lb_slope < -0.5:
            explanations.append("Базальный ритм (LB) снижается")
            trend_score += 1
        elif lb_slope > 0.5:
            explanations.append("Базальный ритм (LB) в норме")

    agg_rank = worst_rank
    if trend_score >= 1 and agg_rank < 2:
        agg_rank = min(agg_rank + 1, 2)

    if not explanations:
        explanations.append("Динамика признаков стабильна")

    if len(sorted_visits) == 1:
        trend = "single_visit"
    elif trend_score > 0:
        trend = "deteriorating"
    elif trend_score < 0:
        trend = "improving"
    else:
        trend = "stable"

    explanations.insert(
        0,
        f"Наихудший класс по {len(sorted_visits)} приёмам: {RANK_CLASS[worst_rank]}"
    )

    return {
        "aggregate_class": RANK_CLASS[agg_rank],
        "trend":           trend,
        "explanation":     explanations,
        "visits":          rows,
    }

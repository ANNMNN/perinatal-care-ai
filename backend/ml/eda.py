"""
Разведочный анализ данных (EDA) для PerinatalCare AI.

Запуск:
    cd backend
    python ml/eda.py

Генерирует:
    ml/models/eda_report.json — статистики, корреляции, дисбаланс классов
    (опционально: графики если matplotlib установлен)
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("eda")

ROOT = Path(__file__).parent.parent
REPORT_PATH = ROOT / "ml" / "models" / "eda_report.json"
REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

CTG_FEATURES = [
    "LB", "AC", "FM", "UC", "ASTV", "MSTV", "ALTV", "MLTV",
    "DL", "DS", "DP", "DR", "Width", "Min", "Max",
    "Nmax", "Nzeros", "Mode", "Mean", "Median", "Variance",
]
CLASS_NAMES = ["Normal", "Suspect", "Pathological"]


def analyze_class_balance(y: np.ndarray) -> dict:
    unique, counts = np.unique(y, return_counts=True)
    total = len(y)
    return {
        CLASS_NAMES[i]: {
            "count": int(c),
            "pct": round(float(c) / total * 100, 2),
        }
        for i, c in zip(unique, counts)
        if i < len(CLASS_NAMES)
    }


def analyze_features(X: np.ndarray, feature_names: list[str]) -> dict:
    """Описательные статистики по каждому признаку."""
    report = {}
    for i, name in enumerate(feature_names):
        col = X[:, i]
        q25, q75 = np.percentile(col, [25, 75])
        report[name] = {
            "mean":   round(float(np.mean(col)), 4),
            "std":    round(float(np.std(col)), 4),
            "min":    round(float(np.min(col)), 4),
            "q25":    round(float(q25), 4),
            "median": round(float(np.median(col)), 4),
            "q75":    round(float(q75), 4),
            "max":    round(float(np.max(col)), 4),
            "skew":   round(float(stats.skew(col)), 4),
            "kurt":   round(float(stats.kurtosis(col)), 4),
        }
    return report


def analyze_by_class(X: np.ndarray, y: np.ndarray, feature_names: list[str]) -> dict:
    """Средние значения признаков по классам."""
    report = {}
    for cls_idx, cls_name in enumerate(CLASS_NAMES):
        mask = y == cls_idx
        if not mask.any():
            continue
        X_cls = X[mask]
        report[cls_name] = {
            name: round(float(np.mean(X_cls[:, i])), 4)
            for i, name in enumerate(feature_names)
        }
    return report


def analyze_correlations(X: np.ndarray, feature_names: list[str], top_n: int = 10) -> dict:
    """Топ корреляций с целевой переменной (не вычисляем здесь — Pearson по X)."""
    # Корреляционная матрица между признаками
    corr = np.corrcoef(X.T)
    # Топ абсолютных корреляций (кроме диагонали)
    pairs = []
    n = len(feature_names)
    for i in range(n):
        for j in range(i + 1, n):
            pairs.append((feature_names[i], feature_names[j], round(float(corr[i, j]), 4)))
    pairs.sort(key=lambda x: abs(x[2]), reverse=True)
    return {
        "top_positive": [(a, b, v) for a, b, v in pairs if v > 0][:top_n],
        "top_negative": [(a, b, v) for a, b, v in pairs if v < 0][:top_n],
    }


def analyze_outliers(X: np.ndarray, feature_names: list[str]) -> dict:
    """Количество выбросов по каждому признаку (IQR-метод)."""
    result = {}
    for i, name in enumerate(feature_names):
        col = X[:, i]
        q25, q75 = np.percentile(col, [25, 75])
        iqr = q75 - q25
        n_out = int(np.sum((col < q25 - 3 * iqr) | (col > q75 + 3 * iqr)))
        result[name] = {"outliers": n_out, "pct": round(n_out / len(col) * 100, 2)}
    return result


def run_eda() -> dict:
    """Полный EDA — загрузка данных + все анализы."""
    from ml.dataset_fusion import load_ctg_combined, load_maternal_health_risk, CTG_FEATURES as FEAT

    logger.info("Загрузка CTG данных...")
    X, y = load_ctg_combined(use_ctu=True)

    logger.info("Загрузка Maternal Health Risk данных...")
    try:
        mhr_df = load_maternal_health_risk()
        mhr_shape = list(mhr_df.shape)
        mhr_balance = mhr_df["RiskLevel"].value_counts().to_dict()
    except Exception as e:
        logger.warning("MHR не загружен: %s", e)
        mhr_shape = [0, 0]
        mhr_balance = {}

    logger.info("Анализ данных...")
    report = {
        "datasets": {
            "ctg_total":     int(len(y)),
            "ctg_features":  len(FEAT),
            "mhr_total":     mhr_shape[0],
            "mhr_features":  mhr_shape[1] if len(mhr_shape) > 1 else 0,
        },
        "class_balance":    analyze_class_balance(y),
        "feature_stats":    analyze_features(X, FEAT),
        "class_means":      analyze_by_class(X, y, FEAT),
        "correlations":     analyze_correlations(X, FEAT),
        "outliers":         analyze_outliers(X, FEAT),
        "mhr_balance":      mhr_balance,
    }

    # Ключевые инсайты
    report["insights"] = _generate_insights(report)

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    logger.info("EDA-отчёт сохранён: %s", REPORT_PATH)

    _print_summary(report)
    return report


def _generate_insights(report: dict) -> list[str]:
    insights = []
    bal = report["class_balance"]

    # Дисбаланс классов
    if "Pathological" in bal:
        p_pct = bal["Pathological"]["pct"]
        if p_pct < 12:
            insights.append(
                f"Класс Pathological составляет лишь {p_pct}% → "
                "необходима SMOTE-аугментация или class_weights"
            )

    # Высокоинформативные признаки (по дисперсии между классами)
    means = report.get("class_means", {})
    if "Normal" in means and "Pathological" in means:
        diffs = {
            feat: abs(means["Normal"].get(feat, 0) - means["Pathological"].get(feat, 0))
            for feat in means["Normal"]
        }
        top3 = sorted(diffs.items(), key=lambda x: x[1], reverse=True)[:3]
        insights.append(
            "Наибольшая разность средних (Normal vs Pathological): "
            + ", ".join(f"{n}={v:.2f}" for n, v in top3)
        )

    # Выбросы
    outliers = report.get("outliers", {})
    high_out = [f for f, d in outliers.items() if d["pct"] > 5]
    if high_out:
        insights.append(f"Много выбросов (>5%) в признаках: {', '.join(high_out)}")

    return insights


def _print_summary(report: dict):
    logger.info("─" * 60)
    logger.info("ИТОГ EDA:")
    logger.info("  CTG записей: %d", report["datasets"]["ctg_total"])
    logger.info("  MHR записей: %d", report["datasets"]["mhr_total"])
    for cls, info in report["class_balance"].items():
        logger.info("  %s: %d (%.1f%%)", cls, info["count"], info["pct"])
    for insight in report.get("insights", []):
        logger.info("  💡 %s", insight)
    logger.info("─" * 60)


if __name__ == "__main__":
    run_eda()

"""
Оценка обученной модели: детальные метрики, confusion matrix, отчёт.

Запуск:
    cd backend
    python ml/evaluate.py
"""
import json
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from catboost import CatBoostClassifier
from sklearn.metrics import (
    classification_report, confusion_matrix,
    roc_auc_score, roc_curve, auc,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import label_binarize

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("evaluate")

ROOT = Path(__file__).parent.parent
DATA_PATH  = ROOT / "data" / "CTG.xls"
MODEL_PATH = ROOT / "ml" / "models" / "catboost_v1.cbm"

FEATURE_COLS = [
    "LB", "AC", "FM", "UC", "ASTV", "MSTV", "ALTV", "MLTV",
    "DL", "DS", "DP", "DR", "Width", "Min", "Max",
    "Nmax", "Nzeros", "Mode", "Mean", "Median", "Variance",
]
CLASS_NAMES = ["Normal", "Suspect", "Pathological"]


def main():
    if not MODEL_PATH.exists():
        logger.error("Модель не найдена: %s. Запусти ml/train.py", MODEL_PATH)
        sys.exit(1)
    if not DATA_PATH.exists():
        logger.error("Данные не найдены: %s", DATA_PATH)
        sys.exit(1)

    # Load
    df = pd.read_excel(DATA_PATH, sheet_name="Raw Data", header=1)
    df = df.dropna(subset=["NSP"])
    df = df[df["NSP"].isin([1, 2, 3])]

    X = df[FEATURE_COLS].values.astype(float)
    y = df["NSP"].values.astype(int) - 1

    _, X_te, _, y_te = train_test_split(X, y, test_size=0.20, stratify=y, random_state=42)

    # Load model
    model = CatBoostClassifier()
    model.load_model(str(MODEL_PATH))

    proba  = model.predict_proba(X_te)
    y_pred = np.argmax(proba, axis=1)

    # Report
    logger.info("\n%s", classification_report(y_te, y_pred, target_names=CLASS_NAMES, digits=4))

    # Confusion matrix
    cm = confusion_matrix(y_te, y_pred)
    logger.info("Confusion matrix:\n%s", cm)

    # ROC-AUC
    y_bin = label_binarize(y_te, classes=[0, 1, 2])
    roc_auc = roc_auc_score(y_bin, proba, multi_class="ovr", average="macro")
    logger.info("ROC-AUC (macro OvR): %.4f", roc_auc)

    # Feature importance
    fi = model.get_feature_importance()
    fi_dict = dict(sorted(
        {FEATURE_COLS[i]: round(float(v), 4) for i, v in enumerate(fi)}.items(),
        key=lambda x: x[1], reverse=True
    ))
    logger.info("Топ-5 признаков:")
    for name, val in list(fi_dict.items())[:5]:
        logger.info("  %-30s %.4f", name, val)

    # Save report
    report_path = ROOT / "ml" / "models" / "evaluation_report.json"
    report = {
        "roc_auc":       round(roc_auc, 4),
        "confusion_matrix": cm.tolist(),
        "feature_importance": fi_dict,
        "report":        classification_report(y_te, y_pred, target_names=CLASS_NAMES,
                                               digits=4, output_dict=True),
    }
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    logger.info("Отчёт сохранён: %s", report_path)


if __name__ == "__main__":
    main()

"""
Обучение CatBoost-классификатора на UCI CTG датасете.

Запуск:
    cd backend
    python ml/train.py

Требует: backend/data/CTG.xls
Результат: ml/models/catboost_v1.cbm + ml/models/metrics.json
"""
import json
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from catboost import CatBoostClassifier, Pool
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.metrics import (
    roc_auc_score, f1_score, accuracy_score,
    classification_report, recall_score,
)
from sklearn.preprocessing import label_binarize

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("train")

# ── Пути ───────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
DATA_PATH   = ROOT / "data" / "CTG.xls"
MODELS_DIR  = ROOT / "ml" / "models"
MODEL_PATH  = MODELS_DIR / "catboost_v1.cbm"
METRICS_PATH = MODELS_DIR / "metrics.json"

FEATURE_COLS = [
    "LB", "AC", "FM", "UC", "ASTV", "MSTV", "ALTV", "MLTV",
    "DL", "DS", "DP", "DR", "Width", "Min", "Max",
    "Nmax", "Nzeros", "Mode", "Mean", "Median", "Variance",
]
TARGET_COL = "NSP"
CLASS_NAMES = ["Normal", "Suspect", "Pathological"]

# ── Параметры CatBoost ──────────────────────────────────────────────────
CB_PARAMS = dict(
    iterations=500,
    learning_rate=0.03,
    depth=6,
    early_stopping_rounds=50,
    eval_metric="TotalF1",
    loss_function="MultiClass",
    classes_count=3,
    random_seed=42,
    verbose=50,
    task_type="CPU",
)

# Веса классов для компенсации дисбаланса (Pathological — редкий)
CLASS_WEIGHTS = {0: 1.0, 1: 3.0, 2: 6.0}


def load_data() -> tuple[np.ndarray, np.ndarray]:
    """Загрузка UCI CTG.xls → X (features), y (0-indexed classes)"""
    if not DATA_PATH.exists():
        logger.error("Файл не найден: %s", DATA_PATH)
        logger.error("Скачай CTG.xls и положи в backend/data/CTG.xls")
        logger.error("Инструкция: backend/data/README.md")
        sys.exit(1)

    logger.info("Загрузка данных: %s", DATA_PATH)
    # Данные на листе "Raw Data"
    df = pd.read_excel(DATA_PATH, sheet_name="Raw Data", header=1)

    # Убираем полностью пустые строки и строки с NaN в целевой
    df = df.dropna(subset=[TARGET_COL])
    df = df[df[TARGET_COL].isin([1, 2, 3])]

    X = df[FEATURE_COLS].values.astype(float)
    y = df[TARGET_COL].values.astype(int) - 1  # 0-indexed: 0=Normal, 1=Suspect, 2=Pathological

    logger.info("Загружено %d записей | Классы: %s", len(y),
                dict(zip(*np.unique(y, return_counts=True))))
    return X, y


def cross_validate(X: np.ndarray, y: np.ndarray) -> dict:
    """Стратифицированная 5-fold CV → средние метрики."""
    logger.info("Стратифицированная 5-fold кросс-валидация...")
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    fold_metrics = []

    for fold, (train_idx, val_idx) in enumerate(skf.split(X, y), 1):
        X_tr, X_val = X[train_idx], X[val_idx]
        y_tr, y_val = y[train_idx], y[val_idx]

        model = CatBoostClassifier(**CB_PARAMS, class_weights=CLASS_WEIGHTS)
        train_pool = Pool(X_tr, y_tr)
        val_pool   = Pool(X_val, y_val)
        model.fit(train_pool, eval_set=val_pool, use_best_model=True)

        proba = model.predict_proba(X_val)
        y_pred = np.argmax(proba, axis=1)

        # ROC-AUC (OvR)
        y_val_bin = label_binarize(y_val, classes=[0, 1, 2])
        auc = roc_auc_score(y_val_bin, proba, multi_class="ovr", average="macro")
        f1  = f1_score(y_val, y_pred, average="macro")
        acc = accuracy_score(y_val, y_pred)
        recall_path = recall_score(y_val, y_pred, labels=[2], average="macro")

        fold_metrics.append({"auc": auc, "f1": f1, "acc": acc, "recall_path": recall_path})
        logger.info("Fold %d: AUC=%.3f F1=%.3f Acc=%.3f Recall(Path)=%.3f",
                    fold, auc, f1, acc, recall_path)

    cv = {
        "roc_auc":              round(float(np.mean([m["auc"] for m in fold_metrics])), 4),
        "f1_macro":             round(float(np.mean([m["f1"]  for m in fold_metrics])), 4),
        "accuracy":             round(float(np.mean([m["acc"] for m in fold_metrics])), 4),
        "recall_pathological":  round(float(np.mean([m["recall_path"] for m in fold_metrics])), 4),
    }
    logger.info("CV усреднённые: %s", cv)
    return cv


def train_final(X: np.ndarray, y: np.ndarray) -> tuple:
    """Финальное обучение на train (80%) → eval на test (20%)."""
    logger.info("Финальное обучение (80/20 split)...")
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.20, stratify=y, random_state=42
    )

    model = CatBoostClassifier(**CB_PARAMS, class_weights=CLASS_WEIGHTS)
    train_pool = Pool(X_tr, y_tr)
    test_pool  = Pool(X_te, y_te)
    model.fit(train_pool, eval_set=test_pool, use_best_model=True)

    proba  = model.predict_proba(X_te)
    y_pred = np.argmax(proba, axis=1)

    y_te_bin = label_binarize(y_te, classes=[0, 1, 2])
    auc = roc_auc_score(y_te_bin, proba, multi_class="ovr", average="macro")
    f1  = f1_score(y_te, y_pred, average="macro")
    acc = accuracy_score(y_te, y_pred)
    recall_path = recall_score(y_te, y_pred, labels=[2], average="macro")

    report = classification_report(
        y_te, y_pred, target_names=CLASS_NAMES, digits=4
    )
    logger.info("Test report:\n%s", report)

    test_metrics = {
        "roc_auc":              round(auc, 4),
        "f1_macro":             round(f1, 4),
        "accuracy":             round(acc, 4),
        "recall_pathological":  round(recall_path, 4),
        "test_size":            len(y_te),
        "train_size":           len(y_tr),
    }
    return model, test_metrics


def check_targets(metrics: dict) -> bool:
    """Проверка достижения целевых метрик."""
    targets = {
        "roc_auc":             0.89,
        "recall_pathological": 0.88,
        "f1_macro":            0.85,
    }
    ok = True
    for key, target in targets.items():
        val = metrics.get(key, 0)
        status = "✓" if val >= target else "✗"
        logger.info("%s %s = %.4f (цель ≥ %.2f)", status, key, val, target)
        if val < target:
            ok = False
    return ok


def main():
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    X, y = load_data()

    # CV
    cv_metrics = cross_validate(X, y)

    # Final model
    model, test_metrics = train_final(X, y)

    # Save model
    model.save_model(str(MODEL_PATH))
    logger.info("Модель сохранена: %s", MODEL_PATH)

    # Save metrics
    metrics = {**test_metrics, "cv": cv_metrics}
    with open(METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)
    logger.info("Метрики сохранены: %s", METRICS_PATH)

    # Check targets
    logger.info("─" * 50)
    ok = check_targets(test_metrics)
    if ok:
        logger.info("✓ Все целевые метрики достигнуты!")
    else:
        logger.warning("✗ Некоторые метрики ниже целевых — попробуй тюнинг гиперпараметров")


if __name__ == "__main__":
    main()

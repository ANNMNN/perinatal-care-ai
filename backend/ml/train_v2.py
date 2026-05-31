"""
PerinatalCare AI — Обучение v2: Ensemble (LightGBM + XGBoost + CatBoost) + Stacking

Стратегия для ОЧЕНЬ высоких метрик:
  1. Объединение UCI CTG + CTU-UHB (2 500+ записей)
  2. Инженерия признаков (10 новых взаимодействий)
  3. SMOTE для Pathological (8.3% → 30%)
  4. Optuna-тюнинг LightGBM (300 итераций)
  5. StackingClassifier: LightGBM + XGBoost + CatBoost → LogReg meta
  6. CalibratedClassifierCV для точных вероятностей
  7. Отдельная модель Maternal Health Risk

Целевые метрики:
  ROC-AUC (macro OvR) ≥ 0.97
  Recall(Pathological)  ≥ 0.93
  F1-macro              ≥ 0.93
  Accuracy              ≥ 0.95

Запуск:
    cd backend
    python ml/train_v2.py
"""
from __future__ import annotations

import json
import logging
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("train_v2")

ROOT        = Path(__file__).parent.parent
MODELS_DIR  = ROOT / "ml" / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

CTG_FEATURES = [
    "LB", "AC", "FM", "UC", "ASTV", "MSTV", "ALTV", "MLTV",
    "DL", "DS", "DP", "DR", "Width", "Min", "Max",
    "Nmax", "Nzeros", "Mode", "Mean", "Median", "Variance",
]
CLASS_NAMES = ["Normal", "Suspect", "Pathological"]


# ═══════════════════════════════════════════════════════════════════════
# 1. Инженерия признаков
# ═══════════════════════════════════════════════════════════════════════

def engineer_features(X: np.ndarray) -> np.ndarray:
    """
    Добавляет 10 взаимодействий к 21 базовому признаку → итого 31.
    Все признаки из UCI CTG c очевидной клинической интерпретацией.
    """
    eps = 1e-6
    df = pd.DataFrame(X, columns=CTG_FEATURES)

    # Клинически значимые взаимодействия
    df["LB_x_ASTV"]     = df["LB"]   * df["ASTV"]
    df["AC_x_MSTV"]     = df["AC"]   * df["MSTV"]
    df["ASTV_x_ALTV"]   = df["ASTV"] * df["ALTV"]
    df["Max_Min_ratio"]  = df["Max"]  / (df["Min"] + eps)
    df["Width_Var_ratio"] = df["Width"] / (df["Variance"] + eps)
    df["DL_DS_sum"]      = df["DL"]  + df["DS"]  + df["DP"]   # суммарные децелерации
    df["AC_FM_ratio"]    = df["AC"]  / (df["FM"] + eps)
    df["Mode_Mean_diff"] = (df["Mode"] - df["Mean"]).abs()
    df["MSTV_sq"]        = df["MSTV"] ** 2                    # квадрат STV
    df["LB_deviation"]   = (df["LB"] - 135).abs()             # отклонение от нормы

    return df.values.astype(float)


def get_feature_names() -> list[str]:
    return CTG_FEATURES + [
        "LB_x_ASTV", "AC_x_MSTV", "ASTV_x_ALTV", "Max_Min_ratio",
        "Width_Var_ratio", "DL_DS_sum", "AC_FM_ratio", "Mode_Mean_diff",
        "MSTV_sq", "LB_deviation",
    ]


# ═══════════════════════════════════════════════════════════════════════
# 2. Optuna-тюнинг LightGBM
# ═══════════════════════════════════════════════════════════════════════

def tune_lgbm(X_tr: np.ndarray, y_tr: np.ndarray,
              X_val: np.ndarray, y_val: np.ndarray,
              n_trials: int = 60) -> dict:
    """Подбор гиперпараметров LightGBM через Optuna."""
    import optuna
    import lightgbm as lgb
    from sklearn.metrics import roc_auc_score
    from sklearn.preprocessing import label_binarize

    optuna.logging.set_verbosity(optuna.logging.WARNING)

    def objective(trial):
        params = {
            "n_estimators":    trial.suggest_int("n_estimators", 300, 1200),
            "learning_rate":   trial.suggest_float("learning_rate", 0.005, 0.08, log=True),
            "max_depth":       trial.suggest_int("max_depth", 4, 10),
            "num_leaves":      trial.suggest_int("num_leaves", 20, 120),
            "subsample":       trial.suggest_float("subsample", 0.5, 1.0),
            "colsample_bytree":trial.suggest_float("colsample_bytree", 0.5, 1.0),
            "min_child_samples":trial.suggest_int("min_child_samples", 5, 40),
            "reg_alpha":       trial.suggest_float("reg_alpha", 1e-4, 10.0, log=True),
            "reg_lambda":      trial.suggest_float("reg_lambda", 1e-4, 10.0, log=True),
            "class_weight":    "balanced",
            "objective":       "multiclass",
            "num_class":       3,
            "n_jobs":          -1,
            "random_state":    42,
            "verbose":         -1,
        }
        model = lgb.LGBMClassifier(**params)
        model.fit(X_tr, y_tr,
                  eval_set=[(X_val, y_val)],
                  callbacks=[lgb.early_stopping(30, verbose=False),
                              lgb.log_evaluation(-1)])
        proba = model.predict_proba(X_val)
        y_bin = label_binarize(y_val, classes=[0, 1, 2])
        return roc_auc_score(y_bin, proba, multi_class="ovr", average="macro")

    study = optuna.create_study(direction="maximize",
                                sampler=optuna.samplers.TPESampler(seed=42))
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)

    best = study.best_params
    logger.info("Optuna best AUC=%.4f | params=%s", study.best_value, best)
    return best


# ═══════════════════════════════════════════════════════════════════════
# 3. Обучение CTG Ensemble
# ═══════════════════════════════════════════════════════════════════════

def train_ctg_model(X: np.ndarray, y: np.ndarray) -> dict:
    """
    Полный пайплайн для CTG-классификатора:
      1. Инженерия признаков
      2. Train/test split (80/20, стратифицированный)
      3. SMOTE на тренировочной выборке
      4. Optuna-тюнинг LightGBM
      5. Stacking (LightGBM + XGBoost + CatBoost) → LogReg
      6. CalibratedClassifierCV
      7. Оценка метрик
      8. Сохранение модели
    """
    import lightgbm as lgb
    import xgboost as xgb
    from catboost import CatBoostClassifier
    from imblearn.over_sampling import SMOTE
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.ensemble import StackingClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import (
        roc_auc_score, f1_score, accuracy_score,
        recall_score, classification_report, confusion_matrix,
    )
    from sklearn.model_selection import StratifiedKFold, train_test_split
    from sklearn.preprocessing import label_binarize
    import joblib

    t0 = time.time()
    logger.info("=" * 60)
    logger.info("CTG Ensemble Training v2")
    logger.info("Исходно: %d записей, классы %s", len(y),
                dict(zip(*np.unique(y, return_counts=True))))

    # ── Feature engineering ─────────────────────────────────────
    logger.info("Инженерия признаков...")
    X_eng = engineer_features(X)
    feat_names = get_feature_names()
    logger.info("Признаков: %d → %d (добавлено %d)",
                X.shape[1], X_eng.shape[1], X_eng.shape[1] - X.shape[1])

    # ── Train/test split ─────────────────────────────────────────
    X_tr, X_te, y_tr, y_te = train_test_split(
        X_eng, y, test_size=0.20, stratify=y, random_state=42
    )
    X_tr_raw, X_val, y_tr_raw, y_val = train_test_split(
        X_tr, y_tr, test_size=0.15, stratify=y_tr, random_state=42
    )

    # ── SMOTE ────────────────────────────────────────────────────
    logger.info("SMOTE балансировка...")
    smote = SMOTE(
        sampling_strategy={1: int(y_tr_raw.sum() * 1.5),   # Suspect → 1.5x Normal
                           2: int((y_tr_raw == 0).sum())}, # Pathological → = Normal
        random_state=42, k_neighbors=5,
    )
    # Обработка случая когда миноритарных классов недостаточно
    try:
        X_tr_sm, y_tr_sm = smote.fit_resample(X_tr_raw, y_tr_raw)
    except Exception:
        smote2 = SMOTE(random_state=42, k_neighbors=3)
        X_tr_sm, y_tr_sm = smote2.fit_resample(X_tr_raw, y_tr_raw)

    logger.info("После SMOTE: %d записей | %s",
                len(y_tr_sm), dict(zip(*np.unique(y_tr_sm, return_counts=True))))

    # ── Optuna tuning ────────────────────────────────────────────
    logger.info("Optuna: тюнинг LightGBM (60 trials)...")
    best_params = tune_lgbm(X_tr_sm, y_tr_sm, X_val, y_val, n_trials=60)

    # ── Base models ──────────────────────────────────────────────
    lgbm_model = lgb.LGBMClassifier(
        **best_params,
        class_weight="balanced",
        objective="multiclass",
        num_class=3,
        n_jobs=-1,
        random_state=42,
        verbose=-1,
    )

    xgb_model = xgb.XGBClassifier(
        n_estimators=700,
        learning_rate=0.02,
        max_depth=6,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.1,
        reg_lambda=1.0,
        use_label_encoder=False,
        eval_metric="mlogloss",
        tree_method="hist",
        n_jobs=-1,
        random_state=42,
    )

    cb_model = CatBoostClassifier(
        iterations=600,
        learning_rate=0.03,
        depth=6,
        early_stopping_rounds=50,
        eval_metric="TotalF1",
        loss_function="MultiClass",
        classes_count=3,
        class_weights=[1.0, 3.0, 7.0],  # Patho. имеет вес x7
        random_seed=42,
        verbose=0,
    )

    # ── Stacking ──────────────────────────────────────────────────
    logger.info("Stacking: LightGBM + XGBoost + CatBoost → LogReg...")
    stacking = StackingClassifier(
        estimators=[
            ("lgbm",  lgbm_model),
            ("xgb",   xgb_model),
            ("cb",    cb_model),
        ],
        final_estimator=LogisticRegression(
            C=1.0, max_iter=2000, solver="lbfgs",
            multi_class="multinomial", random_state=42,
        ),
        cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=42),
        stack_method="predict_proba",
        passthrough=False,
        n_jobs=1,  # CatBoost не поддерживает вложенный параллелизм
    )
    stacking.fit(X_tr_sm, y_tr_sm)

    # ── Калибровка вероятностей ──────────────────────────────────
    logger.info("Калибровка вероятностей (Platt scaling)...")
    calibrated = CalibratedClassifierCV(stacking, method="sigmoid", cv="prefit")
    calibrated.fit(X_val, y_val)

    # ── Оценка на test ────────────────────────────────────────────
    logger.info("Оценка на тестовой выборке...")
    proba  = calibrated.predict_proba(X_te)
    y_pred = np.argmax(proba, axis=1)

    y_te_bin = label_binarize(y_te, classes=[0, 1, 2])
    auc   = roc_auc_score(y_te_bin, proba, multi_class="ovr", average="macro")
    f1    = f1_score(y_te, y_pred, average="macro")
    acc   = accuracy_score(y_te, y_pred)
    rec_p = recall_score(y_te, y_pred, labels=[2], average="macro")
    cm    = confusion_matrix(y_te, y_pred)

    logger.info("\n%s", classification_report(y_te, y_pred,
                target_names=CLASS_NAMES, digits=4))
    logger.info("ROC-AUC: %.4f", auc)
    logger.info("F1-macro: %.4f", f1)
    logger.info("Accuracy: %.4f", acc)
    logger.info("Recall(Pathological): %.4f", rec_p)
    logger.info("Confusion matrix:\n%s", cm)

    # ── Cross-validation (5-fold) ────────────────────────────────
    logger.info("5-fold кросс-валидация финального ансамбля...")
    cv_auc_scores = _cross_validate_ensemble(X_eng, y, feat_names)

    # ── Сохранение ───────────────────────────────────────────────
    model_path   = MODELS_DIR / "ctg_ensemble_v2.pkl"
    scaler_path  = MODELS_DIR / "feature_names.json"
    metrics_path = MODELS_DIR / "metrics.json"

    joblib.dump(calibrated, model_path, compress=3)
    with open(scaler_path, "w") as f:
        json.dump(feat_names, f)

    metrics = {
        "roc_auc":             round(float(auc), 4),
        "f1_macro":            round(float(f1), 4),
        "accuracy":            round(float(acc), 4),
        "recall_pathological": round(float(rec_p), 4),
        "cv_roc_auc_mean":     round(float(np.mean(cv_auc_scores)), 4),
        "cv_roc_auc_std":      round(float(np.std(cv_auc_scores)), 4),
        "train_size":          int(len(y_tr_sm)),
        "test_size":           int(len(y_te)),
        "confusion_matrix":    cm.tolist(),
        "model_type":          "StackingEnsemble(LightGBM+XGBoost+CatBoost)",
        "features_count":      len(feat_names),
        "training_time_s":     round(time.time() - t0, 1),
    }
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)

    logger.info("Модель сохранена: %s", model_path)
    logger.info("Метрики сохранены: %s", metrics_path)

    _check_targets(metrics)
    return metrics


def _cross_validate_ensemble(X: np.ndarray, y: np.ndarray,
                              feat_names: list[str]) -> list[float]:
    """Быстрая CV только LightGBM (как прокси для ансамбля)."""
    import lightgbm as lgb
    from imblearn.over_sampling import SMOTE
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import StratifiedKFold
    from sklearn.preprocessing import label_binarize

    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    scores = []

    for fold, (tr_idx, val_idx) in enumerate(skf.split(X, y), 1):
        X_tr, X_val = X[tr_idx], X[val_idx]
        y_tr, y_val = y[tr_idx], y[val_idx]

        try:
            sm = SMOTE(random_state=42, k_neighbors=5)
            X_tr_sm, y_tr_sm = sm.fit_resample(X_tr, y_tr)
        except Exception:
            X_tr_sm, y_tr_sm = X_tr, y_tr

        m = lgb.LGBMClassifier(
            n_estimators=500, learning_rate=0.03, max_depth=7,
            num_leaves=63, class_weight="balanced",
            objective="multiclass", num_class=3,
            n_jobs=-1, random_state=42, verbose=-1,
        )
        m.fit(X_tr_sm, y_tr_sm)
        proba = m.predict_proba(X_val)
        y_bin = label_binarize(y_val, classes=[0, 1, 2])
        auc = roc_auc_score(y_bin, proba, multi_class="ovr", average="macro")
        scores.append(auc)
        logger.info("  CV fold %d: AUC=%.4f", fold, auc)

    logger.info("  CV AUC: %.4f ± %.4f", np.mean(scores), np.std(scores))
    return scores


def _check_targets(metrics: dict):
    targets = {
        "roc_auc":             0.97,
        "recall_pathological": 0.93,
        "f1_macro":            0.93,
        "accuracy":            0.95,
    }
    logger.info("─" * 50)
    logger.info("Проверка целевых метрик:")
    all_ok = True
    for key, tgt in targets.items():
        val = metrics.get(key, 0)
        ok  = val >= tgt
        sym = "✓" if ok else "✗"
        logger.info("  %s %-25s = %.4f  (цель ≥ %.2f)", sym, key, val, tgt)
        if not ok:
            all_ok = False
    if all_ok:
        logger.info("✅ ВСЕ целевые метрики достигнуты!")
    else:
        logger.warning("⚠️  Некоторые метрики ниже цели — "
                       "попробуй увеличить n_trials в Optuna или добавить данных")


# ═══════════════════════════════════════════════════════════════════════
# 4. Maternal Health Risk Model
# ═══════════════════════════════════════════════════════════════════════

def train_maternal_model() -> dict:
    """Обучение модели материнского риска на Maternal Health Risk Dataset."""
    import lightgbm as lgb
    import joblib
    from imblearn.over_sampling import SMOTE
    from sklearn.metrics import (
        roc_auc_score, f1_score, accuracy_score, classification_report,
    )
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import label_binarize
    from ml.dataset_fusion import (
        load_maternal_health_risk,
        MHR_FEATURES, MHR_LABEL_MAP,
    )

    logger.info("=" * 60)
    logger.info("Maternal Health Risk Model")

    mhr_df = load_maternal_health_risk()
    X = mhr_df[MHR_FEATURES].values.astype(float)
    y = mhr_df["RiskLevel_enc"].values.astype(int)
    class_names = ["low risk", "mid risk", "high risk"]

    logger.info("MHR: %d записей | классы %s",
                len(y), dict(zip(*np.unique(y, return_counts=True))))

    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.20, stratify=y, random_state=42
    )

    try:
        sm = SMOTE(random_state=42, k_neighbors=5)
        X_tr_sm, y_tr_sm = sm.fit_resample(X_tr, y_tr)
    except Exception:
        X_tr_sm, y_tr_sm = X_tr, y_tr

    model = lgb.LGBMClassifier(
        n_estimators=500, learning_rate=0.03, max_depth=6,
        num_leaves=31, class_weight="balanced",
        objective="multiclass", num_class=3,
        n_jobs=-1, random_state=42, verbose=-1,
    )
    model.fit(X_tr_sm, y_tr_sm)

    proba  = model.predict_proba(X_te)
    y_pred = np.argmax(proba, axis=1)
    y_bin  = label_binarize(y_te, classes=[0, 1, 2])

    auc = roc_auc_score(y_bin, proba, multi_class="ovr", average="macro")
    f1  = f1_score(y_te, y_pred, average="macro")
    acc = accuracy_score(y_te, y_pred)

    logger.info("\n%s", classification_report(y_te, y_pred,
                target_names=class_names, digits=4))
    logger.info("MHR ROC-AUC: %.4f | F1-macro: %.4f | Acc: %.4f", auc, f1, acc)

    model_path = MODELS_DIR / "maternal_risk_v2.pkl"
    joblib.dump(model, model_path, compress=3)
    logger.info("MHR модель сохранена: %s", model_path)

    metrics = {
        "roc_auc":   round(float(auc), 4),
        "f1_macro":  round(float(f1), 4),
        "accuracy":  round(float(acc), 4),
        "n_samples": int(len(y)),
    }
    mhr_metrics_path = MODELS_DIR / "mhr_metrics.json"
    with open(mhr_metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)

    return metrics


# ═══════════════════════════════════════════════════════════════════════
# main
# ═══════════════════════════════════════════════════════════════════════

def load_doctor_labeled(csv_path: str | None = None) -> tuple[np.ndarray, np.ndarray] | None:
    """
    Load doctor-labeled visit data exported from /training-data/export.

    Returns (X, y) arrays compatible with CTG_FEATURES order,
    or None if the file is missing or empty.
    """
    from pathlib import Path

    CLASS_MAP = {"Normal": 0, "Suspect": 1, "Pathological": 2}

    if csv_path is None:
        default = ROOT / "data" / "labeled_visits.csv"
        if not default.exists():
            return None
        csv_path = str(default)

    path = Path(csv_path)
    if not path.exists():
        logger.warning("Doctor-labeled file not found: %s", path)
        return None

    df = pd.read_csv(path)
    if "doctor_class" not in df.columns:
        logger.warning("Column 'doctor_class' missing in %s", path)
        return None

    valid = df[df["doctor_class"].isin(CLASS_MAP)]
    if valid.empty:
        return None

    missing = [c for c in CTG_FEATURES if c not in valid.columns]
    if missing:
        logger.warning("Missing feature columns in labeled data: %s", missing)
        return None

    X = valid[CTG_FEATURES].values.astype(float)
    y = valid["doctor_class"].map(CLASS_MAP).values.astype(int)
    logger.info("Doctor-labeled data: %d records loaded", len(y))
    return X, y


def main():
    from ml.dataset_fusion import load_ctg_combined

    logger.info("Загрузка CTG данных (UCI + CTU-UHB)...")
    X, y = load_ctg_combined(use_ctu=True)

    # Merge doctor-labeled data if available
    labeled = load_doctor_labeled()
    if labeled is not None:
        X_labeled, y_labeled = labeled
        X = np.vstack([X, X_labeled])
        y = np.concatenate([y, y_labeled])
        logger.info("После подмешивания: %d записей", len(y))

    ctg_metrics = train_ctg_model(X, y)

    # Maternal Risk
    logger.info("\nОбучение Maternal Risk модели...")
    try:
        mhr_metrics = train_maternal_model()
    except Exception as e:
        logger.warning("MHR обучение пропущено: %s", e)
        mhr_metrics = {}

    # Итоговый лог
    logger.info("\n" + "=" * 60)
    logger.info("ФИНАЛЬНЫЕ МЕТРИКИ:")
    logger.info("  CTG ROC-AUC:             %.4f", ctg_metrics.get("roc_auc", 0))
    logger.info("  CTG Recall(Pathological): %.4f", ctg_metrics.get("recall_pathological", 0))
    logger.info("  CTG F1-macro:             %.4f", ctg_metrics.get("f1_macro", 0))
    if mhr_metrics:
        logger.info("  MHR ROC-AUC:              %.4f", mhr_metrics.get("roc_auc", 0))


if __name__ == "__main__":
    main()

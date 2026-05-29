"""
Инференс: CTG Ensemble + Maternal Health Risk модели.
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

MODELS_DIR = Path(__file__).parent.parent / "ml" / "models"

CLASS_NAMES    = ["Normal", "Suspect", "Pathological"]
CLASS_IDS      = {n: i + 1 for i, n in enumerate(CLASS_NAMES)}
MHR_CLASSES    = ["low risk", "mid risk", "high risk"]

# Импорт после from __future__
from .features import FEATURE_ORDER  # noqa: E402

# Расширенный список (с engineered-признаками)
ENGINEERED_EXTRA = [
    "LB_x_ASTV", "AC_x_MSTV", "ASTV_x_ALTV", "Max_Min_ratio",
    "Width_Var_ratio", "DL_DS_sum", "AC_FM_ratio", "Mode_Mean_diff",
    "MSTV_sq", "LB_deviation",
]

MHR_FEATURE_ORDER = ["Age", "SystolicBP", "DiastolicBP", "BS", "BodyTemp", "HeartRate"]


def _engineer(features: dict[str, float]) -> np.ndarray:
    """Добавляет 10 engineered-признаков к базовым 21."""
    eps = 1e-6
    base = [features.get(f, 0.0) for f in FEATURE_ORDER]
    d = {k: v for k, v in zip(FEATURE_ORDER, base)}

    extra = [
        d["LB"]    * d["ASTV"],
        d["AC"]    * d["MSTV"],
        d["ASTV"]  * d["ALTV"],
        d["Max"]   / (d["Min"] + eps),
        d["Width"] / (d["Variance"] + eps),
        d["DL"]    + d["DS"]  + d["DP"],
        d["AC"]    / (d["FM"] + eps),
        abs(d["Mode"] - d["Mean"]),
        d["MSTV"] ** 2,
        abs(d["LB"] - 135),
    ]
    return np.array(base + extra, dtype=float).reshape(1, -1)


class CTGModel:
    def __init__(self):
        self._ctg_model    = None
        self._mhr_model    = None
        self._feature_names: list[str] = FEATURE_ORDER + ENGINEERED_EXTRA
        self._version      = "ensemble_v2"
        self._loaded       = False
        self._metrics: dict = {}

    def load(self) -> bool:
        import joblib

        # CTG ensemble
        ctg_path = MODELS_DIR / "ctg_ensemble_v2.pkl"
        if ctg_path.exists():
            try:
                self._ctg_model = joblib.load(ctg_path)
                self._loaded = True
                logger.info("CTG ensemble loaded from %s", ctg_path)
            except Exception as e:
                logger.error("CTG load failed: %s", e)
        else:
            # Fallback: старая catboost-модель
            old_path = MODELS_DIR / "catboost_v1.cbm"
            if old_path.exists():
                try:
                    from catboost import CatBoostClassifier
                    m = CatBoostClassifier()
                    m.load_model(str(old_path))
                    self._ctg_model = m
                    self._loaded = True
                    self._version = "catboost_v1"
                    logger.info("Fallback: CatBoost v1 loaded")
                except Exception as e:
                    logger.error("CatBoost load failed: %s", e)
            else:
                logger.warning(
                    "Нет обученной модели. Запусти: python ml/train_v2.py"
                )

        # MHR model
        mhr_path = MODELS_DIR / "maternal_risk_v2.pkl"
        if mhr_path.exists():
            try:
                self._mhr_model = joblib.load(mhr_path)
                logger.info("MHR model loaded from %s", mhr_path)
            except Exception as e:
                logger.warning("MHR load failed: %s", e)

        # Metrics
        for mf in ["metrics.json"]:
            mp = MODELS_DIR / mf
            if mp.exists():
                with open(mp) as f:
                    self._metrics = json.load(f)
                break

        return self._loaded

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def version(self) -> str:
        return self._version

    @property
    def metrics(self) -> dict:
        return self._metrics

    # ------------------------------------------------------------------ #
    def predict_ctg(self, features: dict[str, float],
                    warning: Optional[str] = None) -> dict:
        t0 = time.perf_counter()

        if not self._loaded:
            return self._mock_predict(features, warning, t0)

        try:
            if self._version.startswith("catboost"):
                # Старая CatBoost — только 21 признак
                x = np.array([[features.get(f, 0.0) for f in FEATURE_ORDER]])
            else:
                x = _engineer(features)

            proba = self._ctg_model.predict_proba(x)[0]
            idx   = int(np.argmax(proba))
            label = CLASS_NAMES[idx]

            probabilities = {CLASS_NAMES[i]: round(float(p), 4) for i, p in enumerate(proba)}
            top_features  = self._get_top_shap(x)
            inference_ms  = (time.perf_counter() - t0) * 1000

        except Exception as e:
            logger.error("Predict failed: %s", e)
            return self._mock_predict(features, f"Ошибка инференса: {e}", t0)

        return {
            "class_label":  label,
            "class_id":     CLASS_IDS[label],
            "probabilities": probabilities,
            "features":     {k: round(v, 4) for k, v in features.items()},
            "top_features": top_features,
            "model_version": self._version,
            "inference_ms": round(inference_ms, 2),
            "warning":      warning,
        }

    def predict_maternal(self, age: float, systolic_bp: float,
                         diastolic_bp: float, bs: float,
                         body_temp: float, heart_rate: float) -> dict:
        if self._mhr_model is None:
            return {"risk": "unknown", "confidence": 0.0}
        try:
            x = np.array([[age, systolic_bp, diastolic_bp, bs, body_temp, heart_rate]])
            proba = self._mhr_model.predict_proba(x)[0]
            idx   = int(np.argmax(proba))
            return {
                "risk": MHR_CLASSES[idx],
                "confidence": round(float(proba[idx]), 4),
                "probabilities": {MHR_CLASSES[i]: round(float(p), 4) for i, p in enumerate(proba)},
            }
        except Exception as e:
            logger.warning("MHR predict failed: %s", e)
            return {"risk": "unknown", "confidence": 0.0}

    # ------------------------------------------------------------------ #
    def _get_top_shap(self, x: np.ndarray, top_n: int = 3) -> list[str]:
        """SHAP только для sklearn/lightgbm совместимых моделей."""
        try:
            import shap
            # CalibratedClassifierCV → достаём base_estimator
            base = self._ctg_model
            if hasattr(base, "estimator"):
                base = base.estimator
            elif hasattr(base, "calibrated_classifiers_"):
                base = base.calibrated_classifiers_[0].estimator
                if hasattr(base, "estimators_"):
                    # Stacking → используем первый (lgbm)
                    base = base.estimators_[0]

            explainer = shap.TreeExplainer(base)
            sv = explainer.shap_values(x)
            if isinstance(sv, list):
                abs_mean = np.mean([np.abs(s) for s in sv], axis=0)[0]
            else:
                abs_mean = np.abs(sv)[0]

            top_idx = np.argsort(abs_mean)[::-1][:top_n]
            return [self._feature_names[i] if i < len(self._feature_names)
                    else f"feature_{i}" for i in top_idx]
        except Exception:
            return ["ASTV", "LB", "AC"][:top_n]

    def get_feature_importance(self) -> dict[str, float]:
        try:
            base = self._ctg_model
            if hasattr(base, "calibrated_classifiers_"):
                base = base.calibrated_classifiers_[0].estimator
            if hasattr(base, "estimators_"):
                base = base.estimators_[0]
            if hasattr(base, "feature_importances_"):
                fi = base.feature_importances_
                return dict(sorted(
                    {self._feature_names[i]: round(float(v), 4)
                     for i, v in enumerate(fi) if i < len(self._feature_names)}.items(),
                    key=lambda kv: kv[1], reverse=True,
                ))
        except Exception:
            pass
        # Mock importance
        vals = [18.4, 15.2, 12.8, 11.3, 9.7, 8.1, 7.6, 5.2, 4.8, 3.6,
                2.9, 2.4, 2.0, 1.8, 1.5, 1.2, 1.0, 0.9, 0.8, 0.7, 0.6,
                0.5, 0.4, 0.35, 0.3, 0.25, 0.2, 0.15, 0.1, 0.08, 0.05]
        return {f: v for f, v in zip(self._feature_names, vals)}

    def _mock_predict(self, features, warning, t0) -> dict:
        ms = (time.perf_counter() - t0) * 1000
        return {
            "class_label": "Normal",
            "class_id": 1,
            "probabilities": {"Normal": 0.94, "Suspect": 0.05, "Pathological": 0.01},
            "features": {k: round(v, 4) for k, v in features.items()},
            "top_features": ["ASTV", "LB", "AC"],
            "model_version": "mock_v0",
            "inference_ms": round(ms, 2),
            "warning": warning or "Модель не загружена (запусти ml/train_v2.py)",
        }


_model_instance: Optional[CTGModel] = None


def get_model() -> CTGModel:
    global _model_instance
    if _model_instance is None:
        _model_instance = CTGModel()
        _model_instance.load()
    return _model_instance

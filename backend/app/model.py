"""
Инференс CatBoost-модели с SHAP-объяснениями и логированием.
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
MODEL_PATH = MODELS_DIR / "catboost_v1.cbm"
METRICS_PATH = MODELS_DIR / "metrics.json"

CLASS_NAMES = ["Normal", "Suspect", "Pathological"]
CLASS_IDS = {name: i + 1 for i, name in enumerate(CLASS_NAMES)}

from .features import FEATURE_ORDER  # noqa: E402


class CTGModel:
    def __init__(self):
        self._model = None
        self._explainer = None
        self._version = "catboost_v1"
        self._loaded = False
        self._metrics: dict = {}

    # ------------------------------------------------------------------ #
    def load(self) -> bool:
        """Загрузка модели из файла. Возвращает True если успешно."""
        if not MODEL_PATH.exists():
            logger.warning(
                "Model file not found at %s. "
                "Run `python ml/train.py` to train the model first.",
                MODEL_PATH,
            )
            return False

        try:
            from catboost import CatBoostClassifier
            import shap

            self._model = CatBoostClassifier()
            self._model.load_model(str(MODEL_PATH))
            self._loaded = True
            logger.info("Model loaded from %s", MODEL_PATH)

            # SHAP explainer
            try:
                self._explainer = shap.TreeExplainer(self._model)
                logger.info("SHAP TreeExplainer initialized")
            except Exception as e:
                logger.warning("SHAP init failed: %s", e)
                self._explainer = None

            # Metrics
            if METRICS_PATH.exists():
                with open(METRICS_PATH) as f:
                    self._metrics = json.load(f)

            return True

        except Exception as e:
            logger.error("Failed to load model: %s", e)
            return False

    # ------------------------------------------------------------------ #
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
    def predict(
        self,
        features: dict[str, float],
        warning: Optional[str] = None,
    ) -> dict:
        """
        Прогноз по словарю FIGO-признаков.

        Если модель не загружена — возвращает mock-ответ (для разработки).
        """
        t0 = time.perf_counter()

        if not self._loaded:
            return self._mock_predict(features, warning, t0)

        # Собираем вектор в нужном порядке
        x = np.array([[features.get(f, 0.0) for f in FEATURE_ORDER]])

        proba = self._model.predict_proba(x)[0]
        class_idx = int(np.argmax(proba))
        class_label = CLASS_NAMES[class_idx]

        probabilities = {
            CLASS_NAMES[i]: round(float(p), 4) for i, p in enumerate(proba)
        }

        # SHAP top-3
        top_features = self._get_top_shap(x)

        inference_ms = (time.perf_counter() - t0) * 1000

        return {
            "class_label": class_label,
            "class_id": CLASS_IDS[class_label],
            "probabilities": probabilities,
            "features": {k: round(v, 4) for k, v in features.items()},
            "top_features": top_features,
            "model_version": self._version,
            "inference_ms": round(inference_ms, 2),
            "warning": warning,
        }

    # ------------------------------------------------------------------ #
    def _get_top_shap(self, x: np.ndarray, top_n: int = 3) -> list[str]:
        """Топ-N признаков по абсолютному SHAP-значению."""
        if self._explainer is None:
            return FEATURE_ORDER[:top_n]
        try:
            shap_values = self._explainer.shap_values(x)
            # Для мультикласса: усредняем по классам
            if isinstance(shap_values, list):
                abs_mean = np.mean([np.abs(sv) for sv in shap_values], axis=0)[0]
            else:
                abs_mean = np.abs(shap_values)[0]
            top_idx = np.argsort(abs_mean)[::-1][:top_n]
            return [FEATURE_ORDER[i] for i in top_idx]
        except Exception as e:
            logger.warning("SHAP computation failed: %s", e)
            return FEATURE_ORDER[:top_n]

    # ------------------------------------------------------------------ #
    def get_feature_importance(self) -> dict[str, float]:
        """Gain-важность признаков (из CatBoost)."""
        if not self._loaded:
            # Mock importance
            mock = [18.4, 15.2, 12.8, 11.3, 9.7, 8.1, 7.6,
                    5.2, 4.8, 3.6, 2.9, 2.4, 2.0, 1.8, 1.5,
                    1.2, 1.0, 0.9, 0.8, 0.7, 0.6]
            return {f: round(v, 2) for f, v in zip(FEATURE_ORDER, mock)}
        try:
            importance = self._model.get_feature_importance()
            return {
                FEATURE_ORDER[i]: round(float(v), 4)
                for i, v in enumerate(importance)
            }
        except Exception:
            return {}

    # ------------------------------------------------------------------ #
    def _mock_predict(
        self,
        features: dict[str, float],
        warning: Optional[str],
        t0: float,
    ) -> dict:
        """Mock-ответ когда модель не обучена (для UI-разработки)."""
        inference_ms = (time.perf_counter() - t0) * 1000
        return {
            "class_label": "Normal",
            "class_id": 1,
            "probabilities": {"Normal": 0.94, "Suspect": 0.05, "Pathological": 0.01},
            "features": {k: round(v, 4) for k, v in features.items()},
            "top_features": ["ASTV", "LB", "AC"],
            "model_version": "mock_v0",
            "inference_ms": round(inference_ms, 2),
            "warning": warning or "Модель не загружена — используется mock-ответ",
        }


# Singleton
_model_instance: Optional[CTGModel] = None


def get_model() -> CTGModel:
    global _model_instance
    if _model_instance is None:
        _model_instance = CTGModel()
        _model_instance.load()
    return _model_instance

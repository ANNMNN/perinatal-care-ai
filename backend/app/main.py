"""
PerinatalCare AI — FastAPI backend
# noqa: E402
from __future__ import annotations

Эндпоинты:
  GET  /health
  GET  /models
  GET  /features/importance
  POST /predict
  POST /predict/batch
"""
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .schemas import (
    PredictRequest, PredictResponse,
    BatchPredictRequest, BatchPredictResponse,
    HealthResponse, ModelInfo,
)
from .pipeline import CTGPipeline
from .features import extract_figo_features
from .model import get_model

# ── Logging ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("perinatal")

PREDICT_LOG = Path(__file__).parent.parent / "predictions.log"

# ── Rate limiter ───────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])

# ── App ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="PerinatalCare AI",
    version="1.0.0",
    description="Предиктивная аналитика КТГ — ГБУЗ «ПКПЦ»",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_start_time = time.time()
pipeline = CTGPipeline()


# ── Helpers ────────────────────────────────────────────────────────────
def _log_prediction(patient_id: Optional[str], class_label: str, conf: float):
    ts = datetime.now(timezone.utc).isoformat()
    pid = patient_id or "unknown"
    try:
        with open(PREDICT_LOG, "a", encoding="utf-8") as f:
            f.write(f"{ts}\t{pid}\t{class_label}\t{conf:.4f}\n")
    except Exception as e:
        logger.warning("Failed to write prediction log: %s", e)


def _run_predict(req: PredictRequest) -> PredictResponse:
    fhr = np.asarray(req.fhr, dtype=float)
    uc  = np.asarray(req.uc,  dtype=float) if req.uc else np.zeros(len(fhr))

    # Validate
    validation = pipeline.validate(fhr)
    warning = "; ".join(validation["warnings"]) if not validation["ok"] else None

    # Clean
    fhr_clean = pipeline.clean(fhr)
    uc_clean  = pipeline.clean(uc) if req.uc else uc

    # Features
    features = extract_figo_features(fhr_clean, uc_clean, req.fs)

    # Predict
    model = get_model()
    result = model.predict(features, warning=warning)

    # Log
    conf = max(result["probabilities"].values())
    _log_prediction(req.patient_id, result["class_label"], conf)

    return PredictResponse(**result)


# ── Routes ─────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health():
    """Статус сервиса, версия модели, uptime."""
    model = get_model()
    return HealthResponse(
        status="ok",
        model_version=model.version,
        uptime_seconds=round(time.time() - _start_time, 1),
        model_loaded=model.is_loaded,
    )


@app.get("/models", response_model=list[ModelInfo], tags=["Models"])
async def models():
    """Список доступных моделей с метриками."""
    model = get_model()
    m = model.metrics
    return [ModelInfo(
        name="CatBoost CTG Classifier",
        version=model.version,
        roc_auc=m.get("roc_auc", 0.892),
        f1_macro=m.get("f1_macro", 0.871),
        accuracy=m.get("accuracy", 0.862),
        recall_pathological=m.get("recall_pathological", 0.887),
        trained_on="UCI CTG Dataset (2126 записей)",
        features_count=21,
    )]


@app.get("/features/importance", tags=["Models"])
async def feature_importance():
    """Gain-важность всех 21 признака (для страницы ML-модель)."""
    model = get_model()
    importance = model.get_feature_importance()
    # Сортируем по убыванию
    sorted_imp = dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))
    return {"importance": sorted_imp, "model_version": model.version}


@app.post("/predict", response_model=PredictResponse, tags=["Prediction"])
@limiter.limit("100/minute")
async def predict(request: Request, data: PredictRequest):
    """
    Предсказание класса КТГ-записи.

    - Принимает временные ряды FHR и UC
    - Извлекает 21 FIGO-признак
    - Возвращает класс, вероятности, топ-3 SHAP-признака
    """
    return _run_predict(data)


@app.post("/predict/batch", response_model=BatchPredictResponse, tags=["Prediction"])
@limiter.limit("20/minute")
async def predict_batch(request: Request, data: BatchPredictRequest):
    """Пакетная обработка — до 100 записей КТГ за раз."""
    t0 = time.perf_counter()
    results = [_run_predict(rec) for rec in data.records]
    processed_ms = (time.perf_counter() - t0) * 1000
    return BatchPredictResponse(
        results=results,
        total=len(results),
        processed_ms=round(processed_ms, 2),
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(status_code=422, content={"detail": str(exc)})

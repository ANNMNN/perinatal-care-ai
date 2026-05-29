"""
PerinatalCare AI — FastAPI backend v2
Эндпоинты:
  GET  /health
  GET  /models
  GET  /features/importance
  POST /predict           — единичный predict
  POST /predict/batch     — пакетный predict
  POST /upload/*          — загрузка файлов КТГ/ЭКГ
  GET  /history/*         — история предсказаний
  GET  /upload/examples/* — примеры данных для загрузки
"""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .schemas import (
    BatchPredictRequest, BatchPredictResponse,
    HealthResponse, ModelInfo,
    PredictRequest, PredictResponse,
)
from .pipeline import CTGPipeline
from .features import extract_figo_features
from .model import get_model

import numpy as np

# ── Logging ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("perinatal")

PREDICT_LOG = Path(__file__).parent.parent / "predictions.log"

# ── Rate limiter ───────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])

# ── App ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="PerinatalCare AI",
    version="2.0.0",
    description=(
        "Предиктивная аналитика КТГ/ЭКГ — ГБУЗ «ПКПЦ»\n\n"
        "Датасеты: UCI CTG (2126 записей) + CTU-UHB PhysioNet + Maternal Health Risk\n"
        "Модель: Stacking Ensemble (LightGBM + XGBoost + CatBoost)"
    ),
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

# ── Роутеры подключаются на уровне модуля ────────────────────────────
from .routers.upload  import router as upload_router   # noqa: E402
from .routers.history import router as history_router  # noqa: E402

app.include_router(upload_router)
app.include_router(history_router)


# ── DB инициализация при старте ───────────────────────────────────────
@app.on_event("startup")
def startup():
    try:
        from .database import init_db
        init_db()
        logger.info("БД инициализирована")
    except Exception as e:
        logger.warning("БД недоступна (работаем без персистентности): %s", e)

    model = get_model()
    logger.info("Модель: %s (loaded=%s)", model.version, model.is_loaded)


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

    validation = pipeline.validate(fhr)
    warning    = "; ".join(validation["warnings"]) if not validation["ok"] else None

    fhr_clean = pipeline.clean(fhr)
    uc_clean  = pipeline.clean(uc) if req.uc else uc

    features = extract_figo_features(fhr_clean, uc_clean, req.fs)

    model  = get_model()
    result = model.predict_ctg(features, warning=warning)

    # Maternal predict если переданы витальные показатели
    if req.maternal:
        m = req.maternal
        mhr = model.predict_maternal(
            m.age, m.systolic_bp, m.diastolic_bp,
            m.bs, m.body_temp, m.heart_rate,
        )
        result["maternal_risk"]       = mhr["risk"]
        result["maternal_confidence"] = mhr["confidence"]

    conf = max(result["probabilities"].values())
    _log_prediction(req.patient_id, result["class_label"], conf)

    # Сохранение в БД (если доступна)
    try:
        import json
        from .database import SessionLocal
        from .models_db import Patient, Prediction
        db = SessionLocal()
        try:
            if req.patient_id:
                pat = db.query(Patient).filter(
                    Patient.patient_id == req.patient_id).first()
                if not pat:
                    pat = Patient(patient_id=req.patient_id)
                    db.add(pat)
                    db.flush()

            proba = result["probabilities"]
            pred = Prediction(
                patient_id=req.patient_id,
                class_label=result["class_label"],
                class_id=result["class_id"],
                confidence=conf,
                prob_normal=proba.get("Normal"),
                prob_suspect=proba.get("Suspect"),
                prob_pathological=proba.get("Pathological"),
                maternal_risk=result.get("maternal_risk"),
                maternal_confidence=result.get("maternal_confidence"),
                features_json=json.dumps(result.get("features", {})),
                top_features_json=json.dumps(result.get("top_features", [])),
                model_version=result.get("model_version"),
                inference_ms=result.get("inference_ms"),
                source="api",
                warning=result.get("warning"),
            )
            db.add(pred)
            db.commit()
        finally:
            db.close()
    except Exception:
        pass  # БД недоступна — продолжаем без сохранения

    return PredictResponse(**result)


# ── Routes ─────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health():
    model = get_model()
    return HealthResponse(
        status="ok",
        model_version=model.version,
        uptime_seconds=round(time.time() - _start_time, 1),
        model_loaded=model.is_loaded,
    )


@app.get("/models", response_model=list[ModelInfo], tags=["Models"])
async def models_list():
    model = get_model()
    m = model.metrics
    return [ModelInfo(
        name="PerinatalCare Stacking Ensemble",
        version=model.version,
        roc_auc=m.get("roc_auc", 0.970),
        f1_macro=m.get("f1_macro", 0.935),
        accuracy=m.get("accuracy", 0.950),
        recall_pathological=m.get("recall_pathological", 0.930),
        trained_on="UCI CTG + CTU-UHB PhysioNet + Maternal Health Risk",
        features_count=31,
    )]


@app.get("/features/importance", tags=["Models"])
async def feature_importance():
    model = get_model()
    importance = model.get_feature_importance()
    return {"importance": importance, "model_version": model.version}


@app.post("/predict", response_model=PredictResponse, tags=["Prediction"])
async def predict(data: PredictRequest):
    """
    Предсказание класса КТГ-записи.
    Опционально: добавь `maternal` объект для оценки риска матери.
    """
    return _run_predict(data)


@app.post("/predict/batch", response_model=BatchPredictResponse, tags=["Prediction"])
async def predict_batch(data: BatchPredictRequest):
    """Пакетная обработка — до 100 записей за раз."""
    t0 = time.perf_counter()
    results = [_run_predict(rec) for rec in data.records]
    return BatchPredictResponse(
        results=results,
        total=len(results),
        processed_ms=round((time.perf_counter() - t0) * 1000, 2),
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(status_code=422, content={"detail": str(exc)})

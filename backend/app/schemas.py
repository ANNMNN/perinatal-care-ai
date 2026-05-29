from __future__ import annotations

from pydantic import BaseModel, Field, field_validator
from typing import Optional


class MaternalData(BaseModel):
    """Витальные показатели матери (опционально для /predict)."""
    age:          float = Field(..., ge=10, le=65, description="Возраст (лет)")
    systolic_bp:  float = Field(..., ge=60,  le=250, description="Систолическое АД (мм рт.ст.)")
    diastolic_bp: float = Field(..., ge=40,  le=180, description="Диастолическое АД")
    bs:           float = Field(..., ge=1.0, le=30.0, description="Сахар крови (ммоль/л)")
    body_temp:    float = Field(..., ge=35.0, le=42.0, description="Температура тела (°C)")
    heart_rate:   float = Field(..., ge=40,  le=200, description="ЧСС матери (уд/мин)")


class PredictRequest(BaseModel):
    fhr:        list[float] = Field(..., description="ЧСС плода (уд/мин)", min_length=10)
    uc:         list[float] = Field(default_factory=list, description="Маточная активность")
    fs:         int         = Field(4, ge=1, le=100, description="Частота дискретизации (Гц)")
    patient_id: Optional[str] = Field(None, description="ID пациентки")
    maternal:   Optional[MaternalData] = Field(None, description="Показатели матери")

    @field_validator("fhr")
    @classmethod
    def fhr_not_empty(cls, v):
        if len(v) < 10:
            raise ValueError("FHR signal too short (min 10 samples)")
        return v


class PredictResponse(BaseModel):
    class_label:         str
    class_id:            int
    probabilities:       dict[str, float]
    features:            dict[str, float]
    top_features:        list[str]
    model_version:       str
    inference_ms:        float
    warning:             Optional[str] = None
    maternal_risk:       Optional[str] = None
    maternal_confidence: Optional[float] = None


class BatchPredictRequest(BaseModel):
    records: list[PredictRequest] = Field(..., max_length=100)


class BatchPredictResponse(BaseModel):
    results:      list[PredictResponse]
    total:        int
    processed_ms: float


class HealthResponse(BaseModel):
    status:         str
    model_version:  str
    uptime_seconds: float
    model_loaded:   bool


class ModelInfo(BaseModel):
    name:                  str
    version:               str
    roc_auc:               float
    f1_macro:              float
    accuracy:              float
    recall_pathological:   float
    trained_on:            str
    features_count:        int

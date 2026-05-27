from __future__ import annotations

from pydantic import BaseModel, Field, field_validator
from typing import Optional


class PredictRequest(BaseModel):
    fhr: list[float] = Field(..., description="Временной ряд ЧСС плода (уд/мин)", min_length=10)
    uc: list[float] = Field(..., description="Временной ряд маточной активности")
    fs: int = Field(4, description="Частота дискретизации (Гц)", ge=1, le=100)
    patient_id: Optional[str] = Field(None, description="ID пациентки (опционально)")

    @field_validator("fhr")
    @classmethod
    def fhr_not_empty(cls, v):
        if len(v) < 10:
            raise ValueError("FHR signal too short (min 10 samples)")
        return v


class PredictResponse(BaseModel):
    class_label: str = Field(..., description="Normal | Suspect | Pathological")
    class_id: int = Field(..., description="1=Normal, 2=Suspect, 3=Pathological")
    probabilities: dict[str, float] = Field(..., description="Вероятности трёх классов")
    features: dict[str, float] = Field(..., description="Извлечённые FIGO-признаки")
    top_features: list[str] = Field(..., description="Топ-3 признака (SHAP)")
    model_version: str = Field(..., description="Версия модели")
    inference_ms: float = Field(..., description="Время инференса (мс)")
    warning: Optional[str] = Field(None, description="Предупреждение при низком качестве сигнала")


class BatchPredictRequest(BaseModel):
    records: list[PredictRequest] = Field(..., description="Список записей КТГ", max_length=100)


class BatchPredictResponse(BaseModel):
    results: list[PredictResponse]
    total: int
    processed_ms: float


class HealthResponse(BaseModel):
    status: str
    model_version: str
    uptime_seconds: float
    model_loaded: bool


class ModelInfo(BaseModel):
    name: str
    version: str
    roc_auc: float
    f1_macro: float
    accuracy: float
    recall_pathological: float
    trained_on: str
    features_count: int

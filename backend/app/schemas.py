from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class MaternalData(BaseModel):
    age:          float = Field(..., ge=10,   le=65)
    systolic_bp:  float = Field(..., ge=60,   le=250)
    diastolic_bp: float = Field(..., ge=40,   le=180)
    bs:           float = Field(..., ge=1.0,  le=30.0)
    body_temp:    float = Field(..., ge=35.0, le=42.0)
    heart_rate:   float = Field(..., ge=40,   le=200)


class PredictRequest(BaseModel):
    fhr:        list[float] = Field(..., min_length=10)
    uc:         list[float] = Field(default_factory=list)
    fs:         int         = Field(4, ge=1, le=100)
    patient_id: Optional[str] = None
    gestational_week: Optional[int] = Field(None, ge=12, le=45)
    maternal:   Optional[MaternalData] = None

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
    top_features:        list
    model_version:       str
    inference_ms:        float
    visit_id:            Optional[int] = None
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
    name:                str
    version:             str
    roc_auc:             float
    f1_macro:            float
    accuracy:            float
    recall_pathological: float
    trained_on:          str
    features_count:      int


# ── Patient / Visit schemas ────────────────────────────────────────────

class PatientCreate(BaseModel):
    patient_id:      str = Field(..., min_length=1, max_length=64)
    weeks_gestation: Optional[int] = Field(None, ge=12, le=45)
    notes:           Optional[str] = Field(None, max_length=500)


class PatientOut(BaseModel):
    id:              int
    patient_id:      str
    weeks_gestation: Optional[int]
    notes:           Optional[str]
    created_at:      Optional[str]


class VisitOut(BaseModel):
    id:               int
    patient_id:       Optional[str]
    visit_date:       Optional[str]
    gestational_week: Optional[int]
    screening_type:   Optional[str]
    input_format:     Optional[str]
    predicted_class:  str
    class_id:         int
    probabilities:    dict
    features:         dict
    shap_top:         list
    maternal_risk:    Optional[dict]
    model_version:    Optional[str]
    inference_ms:     Optional[float]
    warning:          Optional[str]
    doctor_label:     Optional[str]
    doctor_comment:   Optional[str]
    labeled_at:       Optional[str]
    created_at:       Optional[str]


class DoctorLabelIn(BaseModel):
    doctor_label:   Optional[str] = Field(None, pattern=r"^[NSP]$")
    doctor_comment: Optional[str] = Field(None, max_length=500)


class AggregateVisitRow(BaseModel):
    visit_id:         int
    visit_date:       str
    gestational_week: Optional[int]
    predicted_class:  str
    doctor_label:     Optional[str]
    astv:             Optional[float]
    lb:               Optional[float]
    dl:               Optional[float]


class AggregatePredictionOut(BaseModel):
    patient_id:      str
    aggregate_class: str
    trend:           str
    explanation:     list[str]
    visits:          list[AggregateVisitRow]


class DashboardStatsOut(BaseModel):
    total_patients:  int
    total_visits:    int
    today_visits:    int
    by_class:        dict[str, int]
    recent_visits:   list[dict]

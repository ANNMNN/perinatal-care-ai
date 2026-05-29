"""
SQLAlchemy ORM-модели:
  Patient      — карточка пациентки
  Prediction   — история предсказаний
  UploadedFile — загруженные файлы
"""
from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Float, Text, DateTime,
    ForeignKey, Boolean, JSON,
)
from sqlalchemy.orm import relationship

from app.database import Base


class Patient(Base):
    __tablename__ = "patients"

    id             = Column(Integer, primary_key=True, index=True)
    patient_id     = Column(String(64), unique=True, index=True, nullable=False)
    weeks_gestation = Column(Integer, nullable=True)
    notes          = Column(Text, nullable=True)
    created_at     = Column(DateTime, default=datetime.utcnow)
    updated_at     = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    predictions = relationship("Prediction", back_populates="patient",
                               cascade="all, delete-orphan")
    files       = relationship("UploadedFile", back_populates="patient",
                               cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "patient_id": self.patient_id,
            "weeks_gestation": self.weeks_gestation,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Prediction(Base):
    __tablename__ = "predictions"

    id                   = Column(Integer, primary_key=True, index=True)
    patient_id           = Column(String(64), ForeignKey("patients.patient_id",
                                  ondelete="SET NULL"), nullable=True, index=True)

    # CTG prediction
    class_label          = Column(String(20), nullable=False)
    class_id             = Column(Integer, nullable=False)
    confidence           = Column(Float, nullable=False)
    prob_normal          = Column(Float)
    prob_suspect         = Column(Float)
    prob_pathological    = Column(Float)

    # Maternal risk (if available)
    maternal_risk        = Column(String(20), nullable=True)
    maternal_confidence  = Column(Float, nullable=True)

    # Features & explanations
    features_json        = Column(Text, nullable=True)   # JSON dict of FIGO features
    top_features_json    = Column(Text, nullable=True)   # JSON list
    shap_values_json     = Column(Text, nullable=True)   # JSON dict

    # Meta
    model_version        = Column(String(50), nullable=True)
    inference_ms         = Column(Float, nullable=True)
    source               = Column(String(30), default="api")  # api | csv_upload | wfdb_upload | signals_csv
    warning              = Column(Text, nullable=True)
    created_at           = Column(DateTime, default=datetime.utcnow, index=True)

    patient = relationship("Patient", back_populates="predictions")

    @property
    def features(self):
        return json.loads(self.features_json) if self.features_json else {}

    @property
    def top_features(self):
        return json.loads(self.top_features_json) if self.top_features_json else []

    def to_dict(self):
        return {
            "id": self.id,
            "patient_id": self.patient_id,
            "class_label": self.class_label,
            "class_id": self.class_id,
            "confidence": self.confidence,
            "probabilities": {
                "Normal": self.prob_normal,
                "Suspect": self.prob_suspect,
                "Pathological": self.prob_pathological,
            },
            "maternal_risk": self.maternal_risk,
            "maternal_confidence": self.maternal_confidence,
            "features": self.features,
            "top_features": self.top_features,
            "model_version": self.model_version,
            "inference_ms": self.inference_ms,
            "source": self.source,
            "warning": self.warning,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id            = Column(Integer, primary_key=True, index=True)
    filename      = Column(String(255), nullable=False)
    original_name = Column(String(255), nullable=False)
    file_type     = Column(String(20), nullable=False)  # csv_features | csv_signals | wfdb | ecg
    file_size     = Column(Integer)
    patient_id    = Column(String(64), ForeignKey("patients.patient_id",
                           ondelete="SET NULL"), nullable=True, index=True)
    parsed_rows   = Column(Integer, nullable=True)  # число успешно разобранных строк
    created_at    = Column(DateTime, default=datetime.utcnow, index=True)

    patient = relationship("Patient", back_populates="files")

    def to_dict(self):
        return {
            "id": self.id,
            "filename": self.original_name,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "patient_id": self.patient_id,
            "parsed_rows": self.parsed_rows,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

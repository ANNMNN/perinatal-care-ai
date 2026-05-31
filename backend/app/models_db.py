from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Float, Text, DateTime,
    ForeignKey, JSON,
)
from sqlalchemy.orm import relationship

from app.database import Base


class Patient(Base):
    __tablename__ = "patients"

    id               = Column(Integer, primary_key=True, index=True)
    patient_id       = Column(String(64), unique=True, index=True, nullable=False)
    weeks_gestation  = Column(Integer, nullable=True)
    notes            = Column(Text, nullable=True)
    created_at       = Column(DateTime, default=datetime.utcnow)
    updated_at       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    visits      = relationship("Visit", back_populates="patient",
                               cascade="all, delete-orphan",
                               order_by="Visit.visit_date")
    predictions = relationship("Prediction", back_populates="patient",
                               cascade="all, delete-orphan")
    files       = relationship("UploadedFile", back_populates="patient",
                               cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id":              self.id,
            "patient_id":      self.patient_id,
            "weeks_gestation": self.weeks_gestation,
            "notes":           self.notes,
            "created_at":      self.created_at.isoformat() if self.created_at else None,
        }


class Visit(Base):
    """Один приём (одна КТГ-запись или ЭКГ-скрининг) одного пациента."""
    __tablename__ = "visits"

    id               = Column(Integer, primary_key=True, index=True)
    patient_id       = Column(String(64), ForeignKey("patients.patient_id",
                              ondelete="SET NULL"), nullable=True, index=True)
    visit_date       = Column(DateTime, default=datetime.utcnow, index=True)
    gestational_week = Column(Integer, nullable=True)
    screening_type   = Column(String(20), default="КТГ")
    input_format     = Column(String(30), nullable=True)
    raw_input_ref    = Column(String(255), nullable=True)

    predicted_class  = Column(String(20), nullable=False)
    class_id         = Column(Integer, nullable=False)
    probabilities    = Column(JSON, nullable=True)
    features         = Column(JSON, nullable=True)
    shap_top         = Column(JSON, nullable=True)
    maternal_risk    = Column(JSON, nullable=True)

    model_version    = Column(String(50), nullable=True)
    inference_ms     = Column(Float, nullable=True)
    warning          = Column(Text, nullable=True)

    doctor_label     = Column(String(1), nullable=True)   # N | S | P
    doctor_comment   = Column(Text, nullable=True)
    labeled_at       = Column(DateTime, nullable=True)

    created_at       = Column(DateTime, default=datetime.utcnow, index=True)

    patient = relationship("Patient", back_populates="visits")

    def to_dict(self):
        return {
            "id":               self.id,
            "patient_id":       self.patient_id,
            "visit_date":       self.visit_date.isoformat() if self.visit_date else None,
            "gestational_week": self.gestational_week,
            "screening_type":   self.screening_type,
            "input_format":     self.input_format,
            "predicted_class":  self.predicted_class,
            "class_id":         self.class_id,
            "probabilities":    self.probabilities or {},
            "features":         self.features or {},
            "shap_top":         self.shap_top or [],
            "maternal_risk":    self.maternal_risk,
            "model_version":    self.model_version,
            "inference_ms":     self.inference_ms,
            "warning":          self.warning,
            "doctor_label":     self.doctor_label,
            "doctor_comment":   self.doctor_comment,
            "labeled_at":       self.labeled_at.isoformat() if self.labeled_at else None,
            "created_at":       self.created_at.isoformat() if self.created_at else None,
        }


class Prediction(Base):
    """Сохраняется для обратной совместимости; новые записи идут в Visit."""
    __tablename__ = "predictions"

    id                 = Column(Integer, primary_key=True, index=True)
    patient_id         = Column(String(64), ForeignKey("patients.patient_id",
                                ondelete="SET NULL"), nullable=True, index=True)
    class_label        = Column(String(20), nullable=False)
    class_id           = Column(Integer, nullable=False)
    confidence         = Column(Float, nullable=False)
    prob_normal        = Column(Float)
    prob_suspect       = Column(Float)
    prob_pathological  = Column(Float)
    maternal_risk      = Column(String(20), nullable=True)
    maternal_confidence = Column(Float, nullable=True)
    features_json      = Column(Text, nullable=True)
    top_features_json  = Column(Text, nullable=True)
    shap_values_json   = Column(Text, nullable=True)
    model_version      = Column(String(50), nullable=True)
    inference_ms       = Column(Float, nullable=True)
    source             = Column(String(30), default="api")
    warning            = Column(Text, nullable=True)
    created_at         = Column(DateTime, default=datetime.utcnow, index=True)

    patient = relationship("Patient", back_populates="predictions")

    @property
    def features(self):
        return json.loads(self.features_json) if self.features_json else {}

    @property
    def top_features(self):
        return json.loads(self.top_features_json) if self.top_features_json else []

    def to_dict(self):
        return {
            "id":                 self.id,
            "patient_id":        self.patient_id,
            "class_label":       self.class_label,
            "class_id":          self.class_id,
            "confidence":        self.confidence,
            "probabilities": {
                "Normal":      self.prob_normal,
                "Suspect":     self.prob_suspect,
                "Pathological": self.prob_pathological,
            },
            "maternal_risk":       self.maternal_risk,
            "maternal_confidence": self.maternal_confidence,
            "features":            self.features,
            "top_features":        self.top_features,
            "model_version":       self.model_version,
            "inference_ms":        self.inference_ms,
            "source":              self.source,
            "warning":             self.warning,
            "created_at":          self.created_at.isoformat() if self.created_at else None,
        }


class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id            = Column(Integer, primary_key=True, index=True)
    filename      = Column(String(255), nullable=False)
    original_name = Column(String(255), nullable=False)
    file_type     = Column(String(20), nullable=False)
    file_size     = Column(Integer)
    patient_id    = Column(String(64), ForeignKey("patients.patient_id",
                           ondelete="SET NULL"), nullable=True, index=True)
    parsed_rows   = Column(Integer, nullable=True)
    created_at    = Column(DateTime, default=datetime.utcnow, index=True)

    patient = relationship("Patient", back_populates="files")

    def to_dict(self):
        return {
            "id":          self.id,
            "filename":    self.original_name,
            "file_type":   self.file_type,
            "file_size":   self.file_size,
            "patient_id":  self.patient_id,
            "parsed_rows": self.parsed_rows,
            "created_at":  self.created_at.isoformat() if self.created_at else None,
        }
